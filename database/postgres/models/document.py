"""
Document and DocumentChunk ORM Models.

Stores uploaded documents (PDF, TXT, DOCX, CSV, JSON, XLSX) and web URLs,
along with their chunk-level metadata in PostgreSQL (Supabase).
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import ForeignKey, Integer, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.postgres.models.base import TimestampMixin
from database.postgres.session import Base


class DocumentRecord(Base, TimestampMixin):
    __tablename__ = "documents"

    doc_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="file")  # "file" | "url"
    source_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    file_type: Mapped[str] = mapped_column(String(32), nullable=False, default="txt")      # "pdf" | "docx" | "txt" | "csv" | "json" | "xlsx" | "url"
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="indexed")    # "processing" | "indexed" | "failed"
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    chunks: Mapped[List[DocumentChunkRecord]] = relationship(
        "DocumentChunkRecord",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<DocumentRecord id={self.id} filename={self.filename!r} status={self.status!r} chunks={self.chunk_count}>"


class DocumentChunkRecord(Base, TimestampMixin):
    __tablename__ = "document_chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    doc_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    chunk_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    faiss_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    document: Mapped[DocumentRecord] = relationship("DocumentRecord", back_populates="chunks")

    def __repr__(self) -> str:
        return f"<DocumentChunkRecord id={self.id} chunk_id={self.chunk_id!r} faiss_id={self.faiss_id}>"
