"""
Document Ingestion and Management Service with Active Document Management.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import UploadFile
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError, ServiceUnavailableError
from app.services.cache_service import get_cache_service
from database.postgres.models.document import DocumentChunkRecord, DocumentRecord
from retrieval.loaders.document_loader import (
    SUPPORTED_EXTENSIONS,
    load_document_from_bytes,
    load_document_from_url,
)
from retrieval.retriever import get_retrieval_pipeline

MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25MB limit


class DocumentService:
    def __init__(self):
        self.pipeline = get_retrieval_pipeline()

    async def upload_file(
        self,
        db: AsyncSession,
        file: UploadFile,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> DocumentRecord:
        filename = Path(file.filename or "unknown.txt").name
        ext = Path(filename).suffix.lower()

        if ext not in SUPPORTED_EXTENSIONS:
            raise ValidationError(
                f"File type '{ext}' is not supported. Supported extensions: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            )

        content_bytes = await file.read()
        if not content_bytes:
            raise ValidationError(f"Uploaded file '{filename}' is empty.")
        if len(content_bytes) > MAX_FILE_SIZE_BYTES:
            raise ValidationError(f"File size exceeds limit of {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB.")

        try:
            document = load_document_from_bytes(content_bytes, filename=filename)
        except Exception as exc:
            logger.error(f"Text extraction failed for '{filename}': {exc}")
            raise ValidationError(f"Failed to extract text from '{filename}': {str(exc)}") from exc

        try:
            chunk_count, chunk_details = self.pipeline.index_document(
                document, chunk_size=chunk_size, chunk_overlap=chunk_overlap
            )
        except Exception as exc:
            logger.error(f"FAISS indexing failed for '{filename}': {exc}")
            raise ServiceUnavailableError(f"Vector indexing failed: {str(exc)}") from exc

        doc_record = await self._save_to_database(
            db=db,
            doc_id=document.doc_id,
            filename=filename,
            source_type="file",
            source_url=None,
            file_type=document.metadata.get("file_type", ext.lstrip(".")),
            file_size=len(content_bytes),
            chunk_count=chunk_count,
            chunk_details=chunk_details,
        )

        # Set as active document immediately
        cache_service = get_cache_service()
        await cache_service.set_active_document_id(doc_record.doc_id)
        await cache_service.invalidate_document_cache(doc_record.doc_id)

        return doc_record

    async def ingest_url(
        self,
        db: AsyncSession,
        url: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> DocumentRecord:
        url = url.strip()
        if not url.startswith("http://") and not url.startswith("https://"):
            raise ValidationError("Invalid URL: must start with http:// or https://")

        try:
            document = load_document_from_url(url)
        except Exception as exc:
            logger.error(f"URL extraction failed for '{url}': {exc}")
            raise ValidationError(f"Failed to fetch content from '{url}': {str(exc)}") from exc

        try:
            chunk_count, chunk_details = self.pipeline.index_document(
                document, chunk_size=chunk_size, chunk_overlap=chunk_overlap
            )
        except Exception as exc:
            logger.error(f"FAISS indexing failed for '{url}': {exc}")
            raise ServiceUnavailableError(f"Vector indexing failed: {str(exc)}") from exc

        doc_record = await self._save_to_database(
            db=db,
            doc_id=document.doc_id,
            filename=document.source_title,
            source_type="url",
            source_url=url,
            file_type="html",
            file_size=len(document.text.encode("utf-8")),
            chunk_count=chunk_count,
            chunk_details=chunk_details,
        )

        cache_service = get_cache_service()
        await cache_service.set_active_document_id(doc_record.doc_id)
        await cache_service.invalidate_document_cache(doc_record.doc_id)

        return doc_record

    async def get_active_document(self, db: AsyncSession) -> Optional[DocumentRecord]:
        cache_service = get_cache_service()
        active_doc_id = await cache_service.get_active_document_id()
        if active_doc_id:
            stmt = select(DocumentRecord).where(DocumentRecord.doc_id == active_doc_id)
            result = await db.execute(stmt)
            doc = result.scalar_one_or_none()
            if doc:
                return doc

        # Fallback to most recently indexed document
        stmt = select(DocumentRecord).order_by(DocumentRecord.indexed_at.desc()).limit(1)
        result = await db.execute(stmt)
        latest_doc = result.scalar_one_or_none()
        if latest_doc:
            await cache_service.set_active_document_id(latest_doc.doc_id)
            return latest_doc
        return None

    async def set_active_document(self, db: AsyncSession, doc_id: str) -> DocumentRecord:
        stmt = select(DocumentRecord).where(DocumentRecord.doc_id == doc_id)
        result = await db.execute(stmt)
        doc = result.scalar_one_or_none()
        if not doc:
            raise NotFoundError(f"Document with doc_id '{doc_id}' not found.")

        cache_service = get_cache_service()
        await cache_service.set_active_document_id(doc_id)
        return doc

    async def list_documents(self, db: AsyncSession) -> Tuple[List[DocumentRecord], int, int]:
        stmt = select(DocumentRecord).order_by(DocumentRecord.indexed_at.desc())
        result = await db.execute(stmt)
        docs = list(result.scalars().all())

        total_docs = len(docs)
        total_chunks = sum(d.chunk_count for d in docs)
        return docs, total_docs, total_chunks

    async def get_document(self, db: AsyncSession, document_id: uuid.UUID) -> DocumentRecord:
        stmt = select(DocumentRecord).where(DocumentRecord.id == document_id)
        result = await db.execute(stmt)
        doc = result.scalar_one_or_none()
        if not doc:
            raise NotFoundError(f"Document with ID '{document_id}' not found.")
        return doc

    async def delete_document(self, db: AsyncSession, document_id: uuid.UUID) -> None:
        stmt = select(DocumentRecord).where(DocumentRecord.id == document_id)
        result = await db.execute(stmt)
        doc = result.scalar_one_or_none()
        if not doc:
            raise NotFoundError(f"Document with ID '{document_id}' not found.")

        doc_id_to_delete = doc.doc_id

        await db.delete(doc)
        await db.commit()

        cache_service = get_cache_service()
        await cache_service.invalidate_document_cache(doc_id_to_delete)

        await self.reindex_all(db)

    async def reindex_all(self, db: AsyncSession) -> Dict[str, Any]:
        stmt = select(DocumentChunkRecord).order_by(DocumentChunkRecord.document_id, DocumentChunkRecord.chunk_index)
        result = await db.execute(stmt)
        chunks = list(result.scalars().all())

        from retrieval.loaders.document_loader import Document
        from retrieval.retriever import RetrievalPipeline

        new_pipeline = RetrievalPipeline()
        docs_by_id: Dict[str, List[DocumentChunkRecord]] = {}
        for c in chunks:
            docs_by_id.setdefault(c.doc_id, []).append(c)

        total_chunks = 0
        for doc_id, doc_chunks in docs_by_id.items():
            first = doc_chunks[0]
            doc = Document(
                doc_id=doc_id,
                source_title=first.chunk_metadata.get("source_title", "Document"),
                source_path=first.chunk_metadata.get("source_path", ""),
                source_url=first.chunk_metadata.get("source_url"),
                text="\n\n".join(c.chunk_text for c in doc_chunks),
                metadata={"file_type": first.chunk_metadata.get("file_type", "txt")},
            )
            count, _ = new_pipeline.index_document(doc)
            total_chunks += count

        self.pipeline.vector_store = new_pipeline.vector_store
        self.pipeline.metadata_store = new_pipeline.metadata_store
        self.pipeline._save()

        return {
            "success": True,
            "message": f"Successfully reindexed {len(docs_by_id)} documents ({total_chunks} chunks).",
            "total_documents": len(docs_by_id),
            "total_chunks": total_chunks,
        }

    async def _save_to_database(
        self,
        db: AsyncSession,
        doc_id: str,
        filename: str,
        source_type: str,
        source_url: Optional[str],
        file_type: str,
        file_size: int,
        chunk_count: int,
        chunk_details: List[Dict[str, Any]],
    ) -> DocumentRecord:
        stmt = select(DocumentRecord).where(DocumentRecord.doc_id == doc_id)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            doc_record = existing
            doc_record.filename = filename
            doc_record.source_type = source_type
            doc_record.source_url = source_url
            doc_record.file_type = file_type
            doc_record.file_size = file_size
            doc_record.chunk_count = chunk_count
            doc_record.status = "indexed"
            from sqlalchemy import delete
            await db.execute(delete(DocumentChunkRecord).where(DocumentChunkRecord.document_id == doc_record.id))
        else:
            doc_record = DocumentRecord(
                doc_id=doc_id,
                filename=filename,
                source_type=source_type,
                source_url=source_url,
                file_type=file_type,
                file_size=file_size,
                chunk_count=chunk_count,
                status="indexed",
            )
            db.add(doc_record)
            await db.flush()

        for c in chunk_details:
            chunk_rec = DocumentChunkRecord(
                document_id=doc_record.id,
                doc_id=doc_id,
                chunk_id=c["chunk_id"],
                faiss_id=c["faiss_id"],
                chunk_index=c["chunk_index"],
                page_number=c.get("page_number"),
                chunk_text=c["text"],
                chunk_metadata={
                    "source_title": filename,
                    "section": c.get("section", "General"),
                    "page_number": c.get("page_number"),
                    "file_type": file_type,
                },
            )
            db.add(chunk_rec)

        await db.commit()
        await db.refresh(doc_record)
        return doc_record


_doc_service = DocumentService()


def get_document_service() -> DocumentService:
    return _doc_service
