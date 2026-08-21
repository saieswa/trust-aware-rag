"""
Retrieval Service.

Thin layer between the API routes and the retrieval pipeline. Its job is to
translate pipeline dataclasses into API response schemas and to turn
pipeline-level problems into our AppError hierarchy, so the route function
itself stays a few lines long and free of business logic.
"""

from typing import Any, Dict, List, Optional

from app.core.exceptions import ServiceUnavailableError, ValidationError
from app.schemas.retrieval import RetrievedChunkResponse
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

    def search(self, query: str, k: int) -> List[RetrievedChunkResponse]:
        try:
            results = self.pipeline.search(query, k=k)
        except Exception as exc:
            raise ServiceUnavailableError(f"Search failed: {exc}") from exc

        return [
            RetrievedChunkResponse(
                chunk_id=r.chunk_id,
                doc_id=r.doc_id,
                text=r.text,
                score=round(r.score, 4),
                source_title=r.source_title,
                source_path=r.source_path,
                chunk_index=r.chunk_index,
            )
            for r in results
        ]

    def stats(self) -> Dict[str, Any]:
        return self.pipeline.stats


_service_singleton: Optional[RetrievalService] = None


def get_retrieval_service() -> RetrievalService:
    global _service_singleton
    if _service_singleton is None:
        _service_singleton = RetrievalService()
    return _service_singleton
