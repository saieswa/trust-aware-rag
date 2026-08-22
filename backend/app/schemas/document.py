"""
Document Management Pydantic Schemas.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class DocumentResponse(BaseModel):
    id: UUID
    doc_id: str
    filename: str
    source_type: str
    source_url: Optional[str] = None
    file_type: str
    status: str
    chunk_count: int
    file_size: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total_documents: int
    total_chunks: int


class URLIngestRequest(BaseModel):
    url: str = Field(..., description="The webpage URL to fetch and index")
    chunk_size: int = Field(default=500, ge=100, le=2000)
    chunk_overlap: int = Field(default=50, ge=0, le=500)


class DocumentUploadResponse(BaseModel):
    success: bool
    message: str
    document: DocumentResponse
