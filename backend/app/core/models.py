import os
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime, ForeignKey, 
    Index, Boolean, JSON, BigInteger
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

def utcnow():
    return datetime.now(timezone.utc)

class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    url_or_path = Column(String(1024), nullable=False)
    default_branch = Column(String(100), default="main")
    status = Column(String(50), default="pending")  # pending, scanning, parsing, indexing, ready, failed
    status_detail = Column(String(500), default="Initialized")
    error_message = Column(Text, nullable=True)
    tech_stack = Column(JSON, default=list)  # detected languages, frameworks, entrypoints
    stats = Column(JSON, default=dict)       # total_files, total_symbols, total_lines
    repo_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    versions = relationship("RepoVersionRecord", back_populates="repo", cascade="all, delete-orphan")
    files = relationship("FileRecord", back_populates="repo", cascade="all, delete-orphan")
    symbols = relationship("SymbolRecord", back_populates="repo", cascade="all, delete-orphan")
    edges = relationship("SymbolEdgeRecord", back_populates="repo", cascade="all, delete-orphan")
    summaries = relationship("FolderSummaryRecord", back_populates="repo", cascade="all, delete-orphan")
    jobs = relationship("JobRecord", back_populates="repo", cascade="all, delete-orphan")
    tours = relationship("TourRecord", back_populates="repo", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSessionRecord", back_populates="repo", cascade="all, delete-orphan")


class RepoVersionRecord(Base):
    __tablename__ = "repo_versions"

    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    commit_sha = Column(String(64), nullable=False)
    indexed_at = Column(DateTime, default=utcnow)

    repo = relationship("Repository", back_populates="versions")


class JobRecord(Base):
    """Tracks background ingestion jobs with idempotent progress and crash safety"""
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    job_type = Column(String(50), default="full_ingest")  # full_ingest, incremental_sync, tour_generation
    status = Column(String(50), default="queued")         # queued, running, completed, failed
    progress_percent = Column(Float, default=0.0)
    current_step = Column(String(255), default="Initialized")
    error = Column(Text, nullable=True)
    started_at = Column(DateTime, default=utcnow)
    finished_at = Column(DateTime, nullable=True)

    repo = relationship("Repository", back_populates="jobs")


class FileRecord(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    version_id = Column(Integer, ForeignKey("repo_versions.id", ondelete="SET NULL"), nullable=True)
    path = Column(String(1024), nullable=False, index=True)
    language = Column(String(50), nullable=True)
    size_bytes = Column(Integer, default=0)
    content_hash = Column(String(64), nullable=False)
    line_count = Column(Integer, default=0)
    importance_score = Column(Float, default=1.0)
    is_entrypoint = Column(Boolean, default=False)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    repo = relationship("Repository", back_populates="files")
    symbols = relationship("SymbolRecord", back_populates="file", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_files_repo_path", "repo_id", "path", unique=True),
    )


class SymbolRecord(Base):
    __tablename__ = "symbols"

    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    file_id = Column(Integer, ForeignKey("files.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("symbols.id", ondelete="SET NULL"), nullable=True)
    parent_symbol_name = Column(String(255), nullable=True)
    name = Column(String(255), nullable=False, index=True)
    qualified_name = Column(String(512), nullable=True, index=True)
    kind = Column(String(50), nullable=False)  # function, class, method, interface
    signature = Column(Text, nullable=True)
    docstring = Column(Text, nullable=True)
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    importance_score = Column(Float, default=1.0)

    repo = relationship("Repository", back_populates="symbols")
    file = relationship("FileRecord", back_populates="symbols")

    __table_args__ = (
        Index("ix_symbols_lookup", "repo_id", "name"),
        Index("ix_symbols_kind", "repo_id", "kind"),
    )


class SymbolEdgeRecord(Base):
    __tablename__ = "symbol_edges"

    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    src_symbol_id = Column(Integer, ForeignKey("symbols.id", ondelete="SET NULL"), nullable=True)
    dst_symbol_id = Column(Integer, ForeignKey("symbols.id", ondelete="SET NULL"), nullable=True)
    source_file = Column(String(1024), nullable=False)
    source_symbol = Column(String(255), nullable=False)
    target_file = Column(String(1024), nullable=True)
    target_symbol = Column(String(255), nullable=False)
    dst_name = Column(String(255), nullable=True)  # Unresolved name kept for Phase 3
    edge_type = Column(String(50), nullable=False)  # calls, defines, imports, inherits
    resolved = Column(Boolean, default=True)

    repo = relationship("Repository", back_populates="edges")

    __table_args__ = (
        Index("ix_edge_source", "repo_id", "source_symbol"),
        Index("ix_edge_target", "repo_id", "target_symbol"),
        Index("ix_edge_type", "repo_id", "edge_type"),
    )


class FolderSummaryRecord(Base):
    __tablename__ = "folder_summaries"

    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    folder_path = Column(String(1024), nullable=False)
    source_hash = Column(String(64), nullable=True)
    summary_text = Column(Text, nullable=False)
    importance_score = Column(Float, default=1.0)
    created_at = Column(DateTime, default=utcnow)

    repo = relationship("Repository", back_populates="summaries")

    __table_args__ = (
        Index("ix_folder_repo_path", "repo_id", "folder_path", unique=True),
    )


class ChunkEmbeddingRecord(Base):
    """
    Chunks table: symbol_id, file_id, text, token_count, embedding, tsv
    Cached by content_hash to never embed identical content twice.
    """
    __tablename__ = "chunk_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    file_id = Column(Integer, ForeignKey("files.id", ondelete="CASCADE"), nullable=True, index=True)
    symbol_id = Column(Integer, ForeignKey("symbols.id", ondelete="CASCADE"), nullable=True, index=True)
    file_path = Column(String(1024), nullable=False)
    symbol_name = Column(String(255), nullable=True)
    chunk_type = Column(String(50), nullable=False)  # symbol, file_summary, folder_summary, repo_summary, tiny_symbols
    start_line = Column(Integer, nullable=True)
    end_line = Column(Integer, nullable=True)
    header = Column(String(512), nullable=True)
    content = Column(Text, nullable=False)
    token_count = Column(Integer, default=0)
    content_hash = Column(String(64), nullable=True, index=True)
    summary = Column(Text, nullable=True)
    importance_score = Column(Float, default=1.0)
    embedding = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    __table_args__ = (
        Index("ix_chunks_repo_file", "repo_id", "file_path"),
        Index("ix_chunks_symbol", "repo_id", "symbol_name"),
        Index("ix_chunks_content_hash", "content_hash"),
    )


class TourRecord(Base):
    __tablename__ = "tours"

    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    tour_type = Column(String(50), default="big_picture")  # big_picture, feature_trace
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    repo = relationship("Repository", back_populates="tours")
    steps = relationship("TourStepRecord", back_populates="tour", cascade="all, delete-orphan", order_by="TourStepRecord.step_order")


class TourStepRecord(Base):
    __tablename__ = "tour_steps"

    id = Column(Integer, primary_key=True, index=True)
    tour_id = Column(Integer, ForeignKey("tours.id", ondelete="CASCADE"), nullable=False, index=True)
    step_order = Column(Integer, nullable=False)
    file_path = Column(String(1024), nullable=False)
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    why_it_matters = Column(Text, nullable=False)
    body = Column(Text, nullable=False)

    tour = relationship("TourRecord", back_populates="steps")


class ChatSessionRecord(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), default="Codebase Discussion")
    created_at = Column(DateTime, default=utcnow)

    repo = relationship("Repository", back_populates="chat_sessions")
    messages = relationship("ChatMessageRecord", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessageRecord.created_at")


class ChatMessageRecord(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    citations = Column(JSON, default=list)     # list of {file_path, start_line, end_line, symbol}
    created_at = Column(DateTime, default=utcnow)

    session = relationship("ChatSessionRecord", back_populates="messages")


class CostTrackingRecord(Base):
    __tablename__ = "cost_tracking"

    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    model_name = Column(String(100), nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    embedding_tokens = Column(Integer, default=0)
    estimated_cost_usd = Column(Float, default=0.0)
    created_at = Column(DateTime, default=utcnow)
