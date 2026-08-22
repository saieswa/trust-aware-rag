"""
Pydantic schemas for the Retrieval API.

These define the exact request/response shapes FastAPI validates against
and shows in Swagger — kept separate from the internal dataclasses in
retrieval/ (Document, Chunk, RetrievedChunk) because API contracts and
internal representations are allowed to evolve independently.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class IndexRequest(BaseModel):
    directory: Optional[str] = Field(
        default=None,
        description="Path to a directory of .txt/.md files to index. Defaults to the sample_documents folder if omitted.",
        examples=["data/sample_documents"],
    )
    chunk_size: int = Field(default=500, ge=100, le=4000, description="Characters per chunk.")
    chunk_overlap: int = Field(default=50, ge=0, le=1000, description="Character overlap between consecutive chunks.")


class IndexResponse(BaseModel):
    documents_indexed: int
    chunks_indexed: int
    message: str


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, examples=["What is the refund policy for late deliveries?"])
    k: int = Field(default=5, ge=1, le=50, description="Number of top results to return.")


class RetrievedChunkResponse(BaseModel):
    chunk_id: str
    doc_id: str
    text: str
    score: float = Field(..., description="Cosine similarity score between 0 and 1 (higher = more similar).")
    source_title: str
    source_path: str
    chunk_index: int
    section: Optional[str] = "General"
    page_number: Optional[int] = None


class SearchResponse(BaseModel):
    query: str
    results: List[RetrievedChunkResponse]
    result_count: int


class RetrievalStatsResponse(BaseModel):
    indexed_chunks: int
    metadata_records: int
    index_path: str
