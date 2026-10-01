import re
import numpy as np
from typing import List, Dict, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.core.models import ChunkEmbeddingRecord, SymbolRecord, FileRecord
from app.llm.provider import LLMProvider, get_llm_provider

class SearchHit:
    def __init__(
        self,
        chunk_id: int,
        file_path: str,
        symbol_name: Optional[str],
        start_line: Optional[int],
        end_line: Optional[int],
        header: Optional[str],
        content: str,
        summary: Optional[str],
        importance_score: float,
        vector_rank: Optional[int] = None,
        keyword_rank: Optional[int] = None,
        rrf_score: float = 0.0,
    ):
        self.chunk_id = chunk_id
        self.file_path = file_path
        self.symbol_name = symbol_name or ""
        self.start_line = start_line or 1
        self.end_line = end_line or 1
        self.header = header or ""
        self.content = content
        self.summary = summary or ""
        self.importance_score = importance_score
        self.vector_rank = vector_rank
        self.keyword_rank = keyword_rank
        self.rrf_score = rrf_score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "file_path": self.file_path,
            "symbol_name": self.symbol_name,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "header": self.header,
            "content": self.content,
            "summary": self.summary,
            "importance_score": self.importance_score,
            "score": round(self.rrf_score, 5)
        }

def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    dot = np.dot(v1, v2)
    norm = np.linalg.norm(v1) * np.linalg.norm(v2)
    if norm < 1e-9:
        return 0.0
    return float(dot / norm)

class HybridSearchEngine:
    def __init__(self, db: Session, repo_id: int, api_key: Optional[str] = None):
        self.db = db
        self.repo_id = repo_id
        self.llm = get_llm_provider(api_key=api_key)

    def search(
        self,
        query: str,
        top_k: int = 15,
        vector_weight: float = 0.6,
        keyword_weight: float = 0.4,
        pagerank_boost: float = 0.3
    ) -> List[SearchHit]:
        """
        Executes hybrid search:
        1. Dense Vector search over ChunkEmbeddingRecord
        2. Sparse Keyword search over symbol names and contents
        3. Reciprocal Rank Fusion (RRF) + PageRank importance weighting
        """
        chunks = self.db.query(ChunkEmbeddingRecord).filter(
            ChunkEmbeddingRecord.repo_id == self.repo_id
        ).all()

        if not chunks:
            return []

        # 1. Vector Search
        query_emb = np.array(self.llm.generate_embeddings([query])[0], dtype=np.float32)
        vector_scores: List[Tuple[ChunkEmbeddingRecord, float]] = []

        for chunk in chunks:
            if chunk.embedding:
                c_emb = np.array(chunk.embedding, dtype=np.float32)
                sim = cosine_similarity(query_emb, c_emb)
                vector_scores.append((chunk, sim))

        vector_scores.sort(key=lambda x: x[1], reverse=True)
        vector_ranks = {item[0].id: rank + 1 for rank, item in enumerate(vector_scores)}

        # 2. Keyword Search
        query_terms = [t.lower() for t in re.findall(r'\w+', query) if len(t) > 1]
        keyword_scores: List[Tuple[ChunkEmbeddingRecord, float]] = []

        for chunk in chunks:
            text_corpus = f"{chunk.file_path} {chunk.symbol_name or ''} {chunk.header or ''} {chunk.content}".lower()
            score = 0.0
            # Exact symbol name match is heavily weighted
            if chunk.symbol_name and chunk.symbol_name.lower() in query.lower():
                score += 10.0

            for term in query_terms:
                count = text_corpus.count(term)
                if count > 0:
                    score += 1.0 + np.log1p(count)

            if score > 0:
                keyword_scores.append((chunk, score))

        keyword_scores.sort(key=lambda x: x[1], reverse=True)
        keyword_ranks = {item[0].id: rank + 1 for rank, item in enumerate(keyword_scores)}

        # 3. Reciprocal Rank Fusion (RRF) with PageRank Boost
        k = 60.0
        combined: Dict[int, Tuple[ChunkEmbeddingRecord, float, Optional[int], Optional[int]]] = {}

        for chunk in chunks:
            cid = chunk.id
            vrank = vector_ranks.get(cid)
            krank = keyword_ranks.get(cid)

            # Skip items that appeared in neither top list if list is long
            if not vrank and not krank:
                continue

            v_term = (vector_weight / (k + vrank)) if vrank else 0.0
            k_term = (keyword_weight / (k + krank)) if krank else 0.0
            raw_rrf = v_term + k_term

            # Apply PageRank multiplier: higher centrality boosts discovery
            imp = getattr(chunk, "importance_score", 1.0) or 1.0
            boosted_score = raw_rrf * (1.0 + pagerank_boost * (imp - 1.0))

            combined[cid] = (chunk, boosted_score, vrank, krank)

        sorted_results = sorted(combined.values(), key=lambda x: x[1], reverse=True)[:top_k]

        hits: List[SearchHit] = []
        for chunk, score, vrank, krank in sorted_results:
            hits.append(
                SearchHit(
                    chunk_id=chunk.id,
                    file_path=chunk.file_path,
                    symbol_name=chunk.symbol_name,
                    start_line=chunk.start_line,
                    end_line=chunk.end_line,
                    header=chunk.header,
                    content=chunk.content,
                    summary=chunk.summary,
                    importance_score=chunk.importance_score or 1.0,
                    vector_rank=vrank,
                    keyword_rank=krank,
                    rrf_score=score
                )
            )

        return hits
