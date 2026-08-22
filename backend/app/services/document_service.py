"""
Document Ingestion and Management Service.

Orchestrates file reading, URL extraction, chunking, FAISS vector indexing,
and PostgreSQL metadata persistence.
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
        """Processes an uploaded file, extracts text, indexes into FAISS, and persists to Supabase."""
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

        # Index in FAISS & in-memory MetadataStore
        try:
            chunk_count, chunk_details = self.pipeline.index_document(
                document, chunk_size=chunk_size, chunk_overlap=chunk_overlap
            )
        except Exception as exc:
            logger.error(f"FAISS indexing failed for '{filename}': {exc}")
            raise ServiceUnavailableError(f"Vector indexing failed: {str(exc)}") from exc

        # Persist DocumentRecord & DocumentChunkRecords to PostgreSQL (Supabase)
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

        return doc_record

    async def ingest_url(
        self,
        db: AsyncSession,
        url: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> DocumentRecord:
        """Fetches a webpage, cleans HTML, indexes into FAISS, and persists to Supabase."""
        url = url.strip()
        if not url.startswith("http://") and not url.startswith("https://"):
            raise ValidationError("Invalid URL: must start with http:// or https://")

        try:
            document = load_document_from_url(url)
        except Exception as exc:
            logger.error(f"Failed to fetch or parse URL '{url}': {exc}")
            raise ValidationError(f"Could not ingest webpage '{url}': {str(exc)}") from exc

        # Index in FAISS
        try:
            chunk_count, chunk_details = self.pipeline.index_document(
                document, chunk_size=chunk_size, chunk_overlap=chunk_overlap
            )
        except Exception as exc:
            logger.error(f"FAISS indexing failed for URL '{url}': {exc}")
            raise ServiceUnavailableError(f"Vector indexing failed: {str(exc)}") from exc

        # Persist to Supabase
        doc_record = await self._save_to_database(
            db=db,
            doc_id=document.doc_id,
            filename=document.title or url,
            source_type="url",
            source_url=url,
            file_type="url",
            file_size=document.metadata.get("size_bytes", len(document.content)),
            chunk_count=chunk_count,
            chunk_details=chunk_details,
        )

        return doc_record

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
        """Saves or updates document and chunk records in PostgreSQL."""
        # Find existing DocumentRecord if any
        stmt = select(DocumentRecord).where(DocumentRecord.doc_id == doc_id)
        result = await db.execute(stmt)
        doc_record = result.scalars().first()

        if doc_record is None:
            doc_record = DocumentRecord(
                doc_id=doc_id,
                filename=filename,
                source_type=source_type,
                source_url=source_url,
                file_type=file_type,
                status="indexed",
                chunk_count=chunk_count,
                file_size=file_size,
            )
            db.add(doc_record)
            await db.flush()  # assign doc_record.id
        else:
            doc_record.filename = filename
            doc_record.source_type = source_type
            doc_record.source_url = source_url
            doc_record.file_type = file_type
            doc_record.status = "indexed"
            doc_record.chunk_count = chunk_count
            doc_record.file_size = file_size
            doc_record.error_message = None
            # Delete old chunks
            await db.execute(
                select(DocumentChunkRecord).where(DocumentChunkRecord.document_id == doc_record.id)
            )
            await db.flush()

        # Insert fresh chunks
        for item in chunk_details:
            chunk_obj = item["chunk"]
            chunk_meta = item["metadata"]
            chunk_record = DocumentChunkRecord(
                document_id=doc_record.id,
                doc_id=doc_id,
                chunk_id=chunk_obj.chunk_id,
                faiss_id=item["faiss_id"],
                chunk_index=chunk_obj.chunk_index,
                page_number=chunk_meta.get("page_number"),
                chunk_text=chunk_obj.text,
                chunk_metadata=chunk_meta,
            )
            db.add(chunk_record)

        await db.commit()
        await db.refresh(doc_record)
        return doc_record

    async def list_documents(self, db: AsyncSession) -> Tuple[List[DocumentRecord], int, int]:
        """Lists all registered documents with total document and chunk counts."""
        stmt = select(DocumentRecord).order_by(DocumentRecord.created_at.desc())
        res = await db.execute(stmt)
        docs = list(res.scalars().all())

        total_docs = len(docs)
        total_chunks = sum(d.chunk_count for d in docs)
        return docs, total_docs, total_chunks

    async def get_document(self, db: AsyncSession, doc_uuid: uuid.UUID) -> DocumentRecord:
        stmt = select(DocumentRecord).where(DocumentRecord.id == doc_uuid)
        res = await db.execute(stmt)
        doc = res.scalars().first()
        if not doc:
            raise NotFoundError(f"Document with ID '{doc_uuid}' not found.")
        return doc

    async def delete_document(self, db: AsyncSession, doc_uuid: uuid.UUID) -> bool:
        """Deletes document from Supabase and purges its vectors from FAISS."""
        doc = await self.get_document(db, doc_uuid)
        doc_id = doc.doc_id

        # Purge from vector store & metadata store, rebuilding FAISS index cleanly
        self.pipeline.delete_document(doc_id)

        # Delete from PostgreSQL (cascade removes document_chunks)
        await db.delete(doc)
        await db.commit()
        logger.info(f"Deleted document record {doc_uuid} ({doc_id}) from database.")
        return True

    async def reindex_all(self, db: AsyncSession) -> Dict[str, Any]:
        """Re-indexes all stored documents from PostgreSQL into FAISS."""
        stmt = select(DocumentRecord)
        res = await db.execute(stmt)
        docs = list(res.scalars().all())

        if not docs:
            # Fallback to sample directory if database has no records yet
            return self.pipeline.index_directory("data/sample_documents")

        # Reset in-memory stores
        self.pipeline.metadata_store = type(self.pipeline.metadata_store)()
        self.pipeline.vector_store = type(self.pipeline.vector_store)(dimension=self.pipeline.embedder.dimension)

        total_chunks = 0
        for doc in docs:
            # Reconstruct chunks from DocumentChunkRecord rows
            chunk_stmt = select(DocumentChunkRecord).where(DocumentChunkRecord.document_id == doc.id).order_by(DocumentChunkRecord.chunk_index)
            c_res = await db.execute(chunk_stmt)
            chunk_records = list(c_res.scalars().all())

            if not chunk_records:
                continue

            texts = [c.chunk_text for c in chunk_records]
            vectors = self.pipeline.embedder.embed(texts)
            ids = []

            for c_rec in chunk_records:
                faiss_id = self.pipeline.metadata_store.next_id()
                ids.append(faiss_id)
                self.pipeline.metadata_store.add(faiss_id, c_rec.chunk_metadata)

            self.pipeline.vector_store.add(vectors, ids)
            total_chunks += len(chunk_records)

        self.pipeline._persist()
        return {
            "documents_indexed": len(docs),
            "chunks_indexed": total_chunks,
            "message": f"Successfully reindexed {len(docs)} document(s) ({total_chunks} chunks).",
        }


_service_singleton: Optional[DocumentService] = None


def get_document_service() -> DocumentService:
    global _service_singleton
    if _service_singleton is None:
        _service_singleton = DocumentService()
    return _service_singleton
