"""
Document Ingestion & Management API Routes.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.database import get_db
from app.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
    URLIngestRequest,
)
from app.services.document_service import DocumentService, get_document_service

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    summary="Upload and index a document file",
)
async def upload_document(
    file: UploadFile = File(...),
    chunk_size: int = Form(default=800),
    chunk_overlap: int = Form(default=100),
    db: AsyncSession = Depends(get_db),
    service: DocumentService = Depends(get_document_service),
) -> DocumentUploadResponse:
    doc_record = await service.upload_file(
        db=db,
        file=file,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return DocumentUploadResponse(
        success=True,
        message=f"Successfully indexed '{doc_record.filename}' ({doc_record.chunk_count} chunks) and set as active document.",
        document=DocumentResponse.model_validate(doc_record),
    )


@router.post(
    "/url",
    response_model=DocumentUploadResponse,
    summary="Fetch and index a webpage URL",
)
async def ingest_url(
    request: URLIngestRequest,
    db: AsyncSession = Depends(get_db),
    service: DocumentService = Depends(get_document_service),
) -> DocumentUploadResponse:
    doc_record = await service.ingest_url(
        db=db,
        url=request.url,
        chunk_size=request.chunk_size,
        chunk_overlap=request.chunk_overlap,
    )
    return DocumentUploadResponse(
        success=True,
        message=f"Successfully indexed webpage '{doc_record.filename}' ({doc_record.chunk_count} chunks) and set as active document.",
        document=DocumentResponse.model_validate(doc_record),
    )


@router.get(
    "/active",
    response_model=Optional[DocumentResponse],
    summary="Get current active document",
)
async def get_active_document(
    db: AsyncSession = Depends(get_db),
    service: DocumentService = Depends(get_document_service),
) -> Optional[DocumentResponse]:
    doc = await service.get_active_document(db)
    if doc:
        return DocumentResponse.model_validate(doc)
    return None


@router.post(
    "/{doc_id}/activate",
    response_model=DocumentResponse,
    summary="Set active document",
)
async def activate_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    doc = await service.set_active_document(db, doc_id)
    return DocumentResponse.model_validate(doc)


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List all indexed documents",
)
async def list_documents(
    db: AsyncSession = Depends(get_db),
    service: DocumentService = Depends(get_document_service),
) -> DocumentListResponse:
    docs, total_docs, total_chunks = await service.list_documents(db)
    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in docs],
        total_documents=total_docs,
        total_chunks=total_chunks,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document details",
)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    doc = await service.get_document(db, document_id)
    return DocumentResponse.model_validate(doc)


@router.delete(
    "/{document_id}",
    summary="Delete a document and purge its vectors",
)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    service: DocumentService = Depends(get_document_service),
) -> dict:
    await service.delete_document(db, document_id)
    return {"success": True, "message": "Document and its vectors successfully deleted."}


@router.post(
    "/reindex",
    summary="Reindex all knowledge documents",
)
async def reindex_documents(
    db: AsyncSession = Depends(get_db),
    service: DocumentService = Depends(get_document_service),
) -> dict:
    result = await service.reindex_all(db)
    return result
