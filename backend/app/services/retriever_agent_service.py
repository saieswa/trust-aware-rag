"""
Retriever Agent Service with Document Scoping.
"""

from typing import Optional

from app.core.exceptions import ServiceUnavailableError
from app.schemas.retriever_agent import EvidenceChunkResponse, RetrieverAgentResponse
from app.services.cache_service import get_cache_service
from agents.retriever.agent import run_retriever_agent


class RetrieverAgentService:
    async def run(self, query: str, k: int, doc_id: Optional[str] = None) -> RetrieverAgentResponse:
        cache_service = get_cache_service()
        effective_doc_id = doc_id or await cache_service.get_active_document_id()

        try:
            final_state = run_retriever_agent(query, k=k, doc_id=effective_doc_id)
        except Exception as exc:
            raise ServiceUnavailableError(f"Retriever Agent failed: {exc}") from exc

        top_evidence = [
            EvidenceChunkResponse(
                chunk_id=item["chunk_id"],
                doc_id=item["doc_id"],
                text=item["text"],
                score=item["score"],
                final_rank_score=item["final_rank_score"],
                source_title=item["source_title"],
                source_path=item["source_path"],
                chunk_index=item["chunk_index"],
                matched_sub_queries=item["matched_sub_queries"],
            )
            for item in final_state.get("top_evidence", [])
        ]

        return RetrieverAgentResponse(
            original_query=final_state["original_query"],
            sub_queries=final_state.get("sub_queries", []),
            decomposition_method=final_state.get("decomposition_method", "none"),
            total_candidates_before_dedup=len(final_state.get("merged_results", [])),
            total_candidates_after_dedup=len(final_state.get("deduplicated_results", [])),
            top_evidence=top_evidence,
        )


_service_singleton: RetrieverAgentService | None = None


def get_retriever_agent_service() -> RetrieverAgentService:
    global _service_singleton
    if _service_singleton is None:
        _service_singleton = RetrieverAgentService()
    return _service_singleton
