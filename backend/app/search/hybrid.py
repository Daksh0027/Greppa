import re
import numpy as np
from typing import List, Dict, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.core.models import ChunkEmbeddingRecord, SymbolRecord, FileRecord
from app.llm.provider import LLMProvider, get_llm_provider

def split_identifiers(text: str) -> List[str]:
    """
    Splits camelCase, PascalCase, snake_case, and kebab-case into lowercase word tokens.
    E.g.: 'refreshToken' -> ['refresh', 'token']
          'APIResponse'  -> ['api', 'response']
          'auth_service' -> ['auth', 'service']
    """
    # 1. Insert space before uppercase letters preceded by lowercase
    s1 = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', text)
    # 2. Insert space before sequence of uppercase letters followed by lowercase (e.g. JSONParser -> JSON Parser)
    s2 = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', s1)
    # 3. Split on underscores, hyphens, and whitespace
    tokens = re.split(r'[_.\-/\s]+', s2)
    return [t.lower() for t in tokens if len(t) > 1]

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
        top_k: int = 8,
        vector_weight: float = 0.6,
        keyword_weight: float = 0.4,
        pagerank_boost: float = 0.35
    ) -> List[SearchHit]:
        """
        Executes hybrid retrieval adhering to Phase 2:
        1. Dense Vector search over ChunkEmbeddingRecord (top 50)
        2. Sparse Keyword search with camelCase/snake_case split tokenization (top 50)
        3. Reciprocal Rank Fusion (RRF) with PageRank weighting
        4. Re-ranks top 20, keeping the best `top_k` (default 8).
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
        # Limit to top 50
        vector_scores = vector_scores[:50]
        vector_ranks = {item[0].id: rank + 1 for rank, item in enumerate(vector_scores)}

        # 2. Keyword Search with camelCase & snake_case identifier preprocessing
        query_terms = split_identifiers(query)
        keyword_scores: List[Tuple[ChunkEmbeddingRecord, float]] = []

        for chunk in chunks:
            raw_text = f"{chunk.file_path} {chunk.symbol_name or ''} {chunk.header or ''} {chunk.content}"
            # Extract normalized identifier tokens from code
            chunk_tokens = split_identifiers(raw_text)
            token_counts = {}
            for t in chunk_tokens:
                token_counts[t] = token_counts.get(t, 0) + 1

            score = 0.0
            # Exact symbol name match heavily boosted
            if chunk.symbol_name and chunk.symbol_name.lower() in query.lower():
                score += 15.0

            # Match split tokens (e.g. 'refresh' and 'token' in 'refreshToken')
            matched_terms = 0
            for term in query_terms:
                count = token_counts.get(term, 0)
                if count > 0:
                    matched_terms += 1
                    score += 1.0 + np.log1p(count)

            # Bonus if multiple query terms hit the same chunk
            if matched_terms > 1:
                score *= (1.0 + 0.25 * matched_terms)

            if score > 0:
                keyword_scores.append((chunk, score))

        keyword_scores.sort(key=lambda x: x[1], reverse=True)
        # Limit to top 50
        keyword_scores = keyword_scores[:50]
        keyword_ranks = {item[0].id: rank + 1 for rank, item in enumerate(keyword_scores)}

        # 3. Reciprocal Rank Fusion (RRF) with PageRank Boost
        k = 60.0
        combined: Dict[int, Tuple[ChunkEmbeddingRecord, float, Optional[int], Optional[int]]] = {}

        for chunk in chunks:
            cid = chunk.id
            vrank = vector_ranks.get(cid)
            krank = keyword_ranks.get(cid)

            if not vrank and not krank:
                continue

            v_term = (vector_weight / (k + vrank)) if vrank else 0.0
            k_term = (keyword_weight / (k + krank)) if krank else 0.0
            raw_rrf = v_term + k_term

            # Apply PageRank centrality prior
            imp = getattr(chunk, "importance_score", 1.0) or 1.0
            boosted_score = raw_rrf * (1.0 + pagerank_boost * (imp - 1.0))

            combined[cid] = (chunk, boosted_score, vrank, krank)

        # Rerank top 20, keeping best top_k (default 8)
        sorted_results = sorted(combined.values(), key=lambda x: x[1], reverse=True)[:20][:top_k]

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
