from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime, ForeignKey, 
    Index, Boolean, JSON
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    url_or_path = Column(String(1024), nullable=False)
    default_branch = Column(String(100), default="main")
    last_commit_hash = Column(String(64), nullable=True)
    status = Column(String(50), default="pending")  # pending, scanning, parsing, indexing, ready, failed
    status_detail = Column(String(500), default="Initialized")
    error_message = Column(Text, nullable=True)
    stats = Column(JSON, default=dict)  # file_count, symbol_count, line_count
    repo_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    files = relationship("FileRecord", back_populates="repo", cascade="all, delete-orphan")
    symbols = relationship("SymbolRecord", back_populates="repo", cascade="all, delete-orphan")
    edges = relationship("SymbolEdgeRecord", back_populates="repo", cascade="all, delete-orphan")
    summaries = relationship("FolderSummaryRecord", back_populates="repo", cascade="all, delete-orphan")


class FileRecord(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    path = Column(String(1024), nullable=False, index=True)
    content_hash = Column(String(64), nullable=False)
    language = Column(String(50), nullable=True)
    line_count = Column(Integer, default=0)
    token_count = Column(Integer, default=0)
    importance_score = Column(Float, default=1.0)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
    name = Column(String(255), nullable=False, index=True)
    kind = Column(String(50), nullable=False)  # function, class, method, interface
    parent_symbol_name = Column(String(255), nullable=True)
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
    source_file = Column(String(1024), nullable=False)
    source_symbol = Column(String(255), nullable=False)
    target_file = Column(String(1024), nullable=True)
    target_symbol = Column(String(255), nullable=False)
    edge_type = Column(String(50), nullable=False)  # calls, defines, imports, inherits

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
    summary_text = Column(Text, nullable=False)
    importance_score = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    repo = relationship("Repository", back_populates="summaries")

    __table_args__ = (
        Index("ix_folder_repo_path", "repo_id", "folder_path", unique=True),
    )


class ChunkEmbeddingRecord(Base):
    """
    Stores vector embeddings and search metadata.
    Supports pgvector (Vector column) when running on PostgreSQL,
    and falls back to JSON float arrays when on SQLite.
    """
    __tablename__ = "chunk_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(String(1024), nullable=False)
    symbol_name = Column(String(255), nullable=True)
    chunk_type = Column(String(50), nullable=False)  # symbol, file_summary, folder_summary, repo_summary
    start_line = Column(Integer, nullable=True)
    end_line = Column(Integer, nullable=True)
    header = Column(String(512), nullable=True)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    importance_score = Column(Float, default=1.0)
    # Stored as JSON list of floats for broad DB compatibility;
    # On PostgreSQL pgvector, an HNSW vector index can also be populated.
    embedding = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_chunks_repo_file", "repo_id", "file_path"),
        Index("ix_chunks_symbol", "repo_id", "symbol_name"),
    )
