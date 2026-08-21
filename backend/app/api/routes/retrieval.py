"""
Retrieval API routes.

Exposes the retrieval pipeline over HTTP:

    POST /api/v1/retrieval/index   — (re)index a directory of documents
    POST /api/v1/retrieval/search  — semantic search over the indexed chunks
    GET  /api/v1/retrieval/stats   — how many chunks/documents are currently indexed

No LLM/agent reasoning happens here — this route only returns raw retrieved
chunks with similarity scores. The Critic Agent (a later step) is what
judges whether those chunks actually support an answer.
"""

from fastapi import APIRouter, Depends

from app.schemas.retrieval import (
    IndexRequest,
    IndexResponse,
    RetrievalStatsResponse,
    SearchRequest,
    SearchResponse,
)
from app.services.retrieval_service import RetrievalService, get_retrieval_service

router = APIRouter(prefix="/retrieval", tags=["Retrieval"])

DEFAULT_SAMPLE_DIRECTORY = "data/sample_documents"


@router.post(
    "/index",
    response_model=IndexResponse,
    summary="Index documents into the vector store",
    description=(
        "Loads every .txt/.md file in the given directory, splits it into "
        "chunks, embeds each chunk with the configured HuggingFace model, "
        "and stores the vectors in FAISS with metadata for retrieval. "
        "Rebuilds the index from scratch on each call."
    ),
)
async def index_documents(
    request: IndexRequest,
    service: RetrievalService = Depends(get_retrieval_service),
) -> IndexResponse:
    directory = request.directory or DEFAULT_SAMPLE_DIRECTORY
    result = service.index_directory(
        directory=directory,
        chunk_size=request.chunk_size,
        chunk_overlap=request.chunk_overlap,
    )
    return IndexResponse(**result)


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Semantic search over indexed chunks",
    description=(
        "Embeds the query and returns the top-k most similar chunks by "
        "cosine similarity, along with their source document and score."
    ),
)
async def search(
    request: SearchRequest,
    service: RetrievalService = Depends(get_retrieval_service),
) -> SearchResponse:
    results = service.search(query=request.query, k=request.k)
    return SearchResponse(query=request.query, results=results, result_count=len(results))


@router.get(
    "/stats",
    response_model=RetrievalStatsResponse,
    summary="Current index statistics",
    description="Returns how many chunks are currently indexed and where the index is stored on disk.",
)
async def stats(
    service: RetrievalService = Depends(get_retrieval_service),
) -> RetrievalStatsResponse:
    return RetrievalStatsResponse(**service.stats())
