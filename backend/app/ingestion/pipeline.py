import os
import hashlib
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple, Set, Any
from sqlalchemy.orm import Session
from app.core.models import (
    Repository, FileRecord, SymbolRecord, SymbolEdgeRecord,
    FolderSummaryRecord, ChunkEmbeddingRecord
)
from app.ingestion.scanner import scan_repository, ScannedFile
from app.ingestion.parser import parse_code_file, ParsedFile
from app.ingestion.graph_builder import SymbolGraph
from app.ingestion.chunker import chunk_file_by_symbols, SymbolChunk
from app.ingestion.summarizer import HierarchicalSummarizer
from app.llm.provider import LLMProvider, get_llm_provider

logger = logging.getLogger("greppa.pipeline")

class IngestionPipeline:
    def __init__(self, db: Session, repo_id: int, api_key: Optional[str] = None):
        self.db = db
        self.repo_id = repo_id
        self.llm = get_llm_provider(api_key=api_key)
        self.summarizer = HierarchicalSummarizer(self.llm)

    def run(self, repo_dir: str, incremental: bool = True) -> Dict[str, Any]:
        """
        Executes the end-to-end ingestion pipeline:
        Scan -> AST Parse -> Symbol Graph -> PageRank -> Bottom-Up Summarize -> Embed -> Save.
        Supports fast incremental invalidation via content hashes.
        """
        repo = self.db.query(Repository).filter(Repository.id == self.repo_id).first()
        if not repo:
            raise ValueError(f"Repository with id {self.repo_id} not found")

        repo.status = "scanning"
        repo.status_detail = "Scanning file tree and computing content hashes..."
        self.db.commit()

        from app.core.models import JobRecord, RepoVersionRecord
        from app.ingestion.analyzer import analyze_tech_stack_and_entrypoints

        # Register or update background job
        job = self.db.query(JobRecord).filter(
            JobRecord.repo_id == self.repo_id,
            JobRecord.status.in_(["queued", "running"])
        ).first()
        if not job:
            job = JobRecord(
                repo_id=self.repo_id,
                job_type="incremental_sync" if incremental else "full_ingest",
                status="running",
                progress_percent=15.0,
                current_step="Scanning file tree"
            )
            self.db.add(job)
            self.db.commit()

        # Step 1: Scan files with gitignore and size filters
        scanned_files = scan_repository(repo_dir)
        scanned_by_path: Dict[str, ScannedFile] = {f.rel_path: f for f in scanned_files}

        # Analyze tech stack & entrypoints
        analysis = analyze_tech_stack_and_entrypoints(repo_dir, list(scanned_by_path.keys()))
        repo.tech_stack = analysis

        # Record repo version / commit SHA if git
        commit_sha = "local_" + hashlib.sha256(str(len(scanned_files)).encode()).hexdigest()[:12]
        if os.path.exists(os.path.join(repo_dir, ".git")):
            try:
                import subprocess
                res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dir, capture_output=True, text=True)
                if res.returncode == 0:
                    commit_sha = res.stdout.strip()
            except Exception:
                pass

        version_rec = RepoVersionRecord(repo_id=self.repo_id, commit_sha=commit_sha)
        self.db.add(version_rec)
        self.db.flush()

        # Step 2: Incremental diff computation
        job.progress_percent = 30.0
        job.current_step = "Computing file content hash diff"
        self.db.commit()
        existing_files = self.db.query(FileRecord).filter(FileRecord.repo_id == self.repo_id).all()
        existing_by_path: Dict[str, FileRecord] = {f.path: f for f in existing_files}

        to_process_paths: Set[str] = set()
        unchanged_paths: Set[str] = set()
        deleted_paths: Set[str] = set()

        if incremental and existing_files:
            for path, scanned in scanned_by_path.items():
                if path not in existing_by_path:
                    to_process_paths.add(path)
                elif existing_by_path[path].content_hash != scanned.content_hash:
                    to_process_paths.add(path)
                else:
                    unchanged_paths.add(path)

            for path in existing_by_path:
                if path not in scanned_by_path:
                    deleted_paths.add(path)

            # Invalidate direct dependents of modified/deleted files
            impacted = to_process_paths.union(deleted_paths)
            if impacted:
                dependent_edges = self.db.query(SymbolEdgeRecord).filter(
                    SymbolEdgeRecord.repo_id == self.repo_id,
                    SymbolEdgeRecord.target_file.in_(impacted)
                ).all()
                for edge in dependent_edges:
                    if edge.source_file in scanned_by_path:
                        to_process_paths.add(edge.source_file)
        else:
            to_process_paths = set(scanned_by_path.keys())

        logger.info(
            f"Ingestion diff for repo {repo.name}: {len(to_process_paths)} to process, "
            f"{len(unchanged_paths)} unchanged, {len(deleted_paths)} deleted."
        )

        repo.status = "parsing"
        repo.status_detail = f"Parsing {len(scanned_files)} files into AST symbol graph..."
        self.db.commit()

        # Step 3: Parse files with Tree-sitter / AST
        graph = SymbolGraph()
        parsed_files: Dict[str, ParsedFile] = {}

        for path, sc in scanned_by_path.items():
            code = sc.read_text()
            parsed = parse_code_file(code, path, sc.language)
            parsed_files[path] = parsed
            graph.add_file(parsed)

        # Step 4: Resolve call graph edges and compute PageRank
        graph.build_edges()
        node_scores = graph.compute_pagerank()
        file_scores = graph.get_file_importance_scores(node_scores)

        # Step 5: Clean up deleted or modified file records in DB
        paths_to_clean = to_process_paths.union(deleted_paths)
        if paths_to_clean:
            self.db.query(ChunkEmbeddingRecord).filter(
                ChunkEmbeddingRecord.repo_id == self.repo_id,
                ChunkEmbeddingRecord.file_path.in_(paths_to_clean)
            ).delete(synchronize_session=False)

            self.db.query(SymbolEdgeRecord).filter(
                SymbolEdgeRecord.repo_id == self.repo_id,
                SymbolEdgeRecord.source_file.in_(paths_to_clean)
            ).delete(synchronize_session=False)

            self.db.query(FileRecord).filter(
                FileRecord.repo_id == self.repo_id,
                FileRecord.path.in_(paths_to_clean)
            ).delete(synchronize_session=False)
            self.db.commit()

        repo.status = "summarizing"
        repo.status_detail = "Generating bottom-up hierarchical summaries and symbol chunks..."
        self.db.commit()

        # Step 6: Bottom-Up Hierarchical Summarization & Symbol Chunking
        file_summaries: Dict[str, str] = {}
        all_chunks: List[SymbolChunk] = []

        for path, sc in scanned_by_path.items():
            parsed = parsed_files[path]
            code = sc.read_text()
            file_score = file_scores.get(path, 1.0)

            # Check if summary can be reused from cache
            cached_sum = existing_by_path[path].summary if path in unchanged_paths and path in existing_by_path else None
            f_summary, sym_summaries = self.summarizer.summarize_file(parsed, sc.content_hash, cached_sum)
            file_summaries[path] = f_summary

            # Only re-chunk and re-save if file was marked for processing or new
            if path in to_process_paths or not incremental:
                f_record = FileRecord(
                    repo_id=self.repo_id,
                    path=path,
                    content_hash=sc.content_hash,
                    language=sc.language,
                    line_count=sc.line_count,
                    importance_score=file_score,
                    summary=f_summary
                )
                self.db.add(f_record)
                self.db.flush()

                # Save symbols
                for sym in parsed.symbols:
                    sym_node_id = f"sym:{path}:{sym.name}"
                    sym_score = node_scores.get(sym_node_id, 1.0)
                    s_record = SymbolRecord(
                        repo_id=self.repo_id,
                        file_id=f_record.id,
                        name=sym.name,
                        kind=sym.kind,
                        parent_symbol_name=sym.parent_name,
                        signature=sym.signature,
                        docstring=sym.docstring,
                        start_line=sym.start_line,
                        end_line=sym.end_line,
                        content=sym.content,
                        summary=sym_summaries.get(sym.name, ""),
                        importance_score=sym_score
                    )
                    self.db.add(s_record)

                # Chunks for embedding
                chunks = chunk_file_by_symbols(parsed, code, node_scores)
                all_chunks.extend(chunks)
            else:
                # Update importance score on unchanged file
                if path in existing_by_path:
                    existing_by_path[path].importance_score = file_score

        # Save symbol edges into DB
        for u, v, data in graph.graph.edges(data=True):
            edge_type = data.get("edge_type", "calls")
            u_data = graph.graph.nodes.get(u, {})
            v_data = graph.graph.nodes.get(v, {})
            source_file = u_data.get("path", "")
            target_file = v_data.get("path", "")
            source_sym = u_data.get("label", u)
            target_sym = v_data.get("label", v)

            if source_file in to_process_paths or not incremental:
                edge_rec = SymbolEdgeRecord(
                    repo_id=self.repo_id,
                    source_file=source_file,
                    source_symbol=source_sym,
                    target_file=target_file,
                    target_symbol=target_sym,
                    edge_type=edge_type
                )
                self.db.add(edge_rec)

        # Folder & Whole-Repo Summaries
        folder_summaries = self.summarizer.summarize_folders(file_summaries)
        repo_summary = self.summarizer.summarize_repository(folder_summaries, repo.name)
        repo.repo_summary = repo_summary

        # Save folder summaries
        self.db.query(FolderSummaryRecord).filter(FolderSummaryRecord.repo_id == self.repo_id).delete(synchronize_session=False)
        for folder, f_sum in folder_summaries.items():
            self.db.add(FolderSummaryRecord(
                repo_id=self.repo_id,
                folder_path=folder,
                summary_text=f_sum
            ))

        repo.status = "indexing"
        repo.status_detail = f"Generating vector embeddings for {len(all_chunks)} symbol chunks..."
        self.db.commit()

        # Step 7: Embeddings & Vector Storage
        if all_chunks:
            # Batch embeddings in chunks of 50
            batch_size = 50
            for i in range(0, len(all_chunks), batch_size):
                chunk_batch = all_chunks[i : i + batch_size]
                texts = [c.get_embedding_text() for c in chunk_batch]
                embeddings = self.llm.generate_embeddings(texts)

                for chunk, emb in zip(chunk_batch, embeddings):
                    chunk_rec = ChunkEmbeddingRecord(
                        repo_id=self.repo_id,
                        file_path=chunk.file_path,
                        symbol_name=chunk.symbol_name,
                        chunk_type="symbol",
                        start_line=chunk.start_line,
                        end_line=chunk.end_line,
                        header=chunk.signature,
                        content=chunk.content,
                        summary=chunk.docstring,
                        importance_score=chunk.importance_score,
                        embedding=emb
                    )
                    self.db.add(chunk_rec)
            self.db.commit()

        # Step 8: Finalize Repo Stats & State
        total_syms = self.db.query(SymbolRecord).filter(SymbolRecord.repo_id == self.repo_id).count()
        total_files = len(scanned_files)
        total_lines = sum(f.line_count for f in scanned_files)

        repo.stats = {
            "total_files": total_files,
            "total_symbols": total_syms,
            "total_lines": total_lines,
            "processed_files": len(to_process_paths),
            "unchanged_files": len(unchanged_paths)
        }
        repo.status = "ready"
        repo.status_detail = "Index is active and ready for queries"

        # Finalize job record
        if job:
            job.status = "completed"
            job.progress_percent = 100.0
            job.current_step = "Ingestion complete"
            job.finished_at = datetime.now(timezone.utc)

        self.db.commit()

        return repo.stats
