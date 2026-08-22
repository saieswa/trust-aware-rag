"""
Retrieval Service with Document Scoping and Redis Caching.
"""

from typing import Any, Dict, List, Optional

from app.core.exceptions import ServiceUnavailableError, ValidationError
from app.schemas.retrieval import RetrievedChunkResponse
from app.services.cache_service import get_cache_service
from retrieval.retriever import get_retrieval_pipeline


class RetrievalService:
    def __init__(self):
        self.pipeline = get_retrieval_pipeline()

    def index_directory(self, directory: str, chunk_size: int, chunk_overlap: int) -> Dict[str, Any]:
        try:
            return self.pipeline.index_directory(
                directory, chunk_size=chunk_size, chunk_overlap=chunk_overlap
            )
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        except Exception as exc:
            raise ServiceUnavailableError(f"Indexing failed: {exc}") from exc

    async def search(self, query: str, k: int, doc_id: Optional[str] = None) -> List[RetrievedChunkResponse]:
        cache_service = get_cache_service()
        effective_doc_id = doc_id or await cache_service.get_active_document_id()

        # Check cache
        if effective_doc_id:
            cached_data = await cache_service.get_cached("retrieval", effective_doc_id, query)
            if cached_data:
                return [RetrievedChunkResponse(**c) for c in cached_data]

        try:
            results = self.pipeline.search(query, k=k, doc_id=effective_doc_id)
        except Exception as exc:
            raise ServiceUnavailableError(f"Search failed: {exc}") from exc

        chunk_responses = [
            RetrievedChunkResponse(
                chunk_id=r.chunk_id,
                doc_id=r.doc_id,
                text=r.text,
                score=round(r.score, 4),
                source_title=r.source_title,
                source_path=r.source_path,
                chunk_index=r.chunk_index,
                section=getattr(r, "section", "General"),
                page_number=getattr(r, "page_number", None),
            )
            for r in results
        ]

        if effective_doc_id:
            await cache_service.set_cached(
                "retrieval",
                effective_doc_id,
                query,
                [c.model_dump() for c in chunk_responses],
            )

        return chunk_responses

    def stats(self) -> Dict[str, Any]:
        return self.pipeline.stats


_service_singleton: Optional[RetrievalService] = None


def get_retrieval_service() -> RetrievalService:
    global _service_singleton
    if _service_singleton is None:
        _service_singleton = RetrievalService()
    return _service_singleton
