"""
Synthesis Service with Document Scoping and Redis Caching.
"""

from typing import Any, Dict, Optional

from loguru import logger
from app.core.exceptions import ServiceUnavailableError
from app.schemas.synthesis import CitationResponse, SentenceVerdictResponse, StructuredAnswer, SynthesisResponse
from app.services.cache_service import get_cache_service
from agents.pipeline.agent import run_full_pipeline
from agents.retriever.query_analyzer import classify_query_type
from trust.trust_engine import compute_trust_report


class SynthesisService:
    async def run(
        self,
        query: str,
        k: int,
        max_retries: int,
        trust_report: Optional[Dict[str, Any]],
        doc_id: Optional[str] = None,
    ) -> SynthesisResponse:
        cache_service = get_cache_service()
        effective_doc_id = doc_id or await cache_service.get_active_document_id()

        if not effective_doc_id:
            return SynthesisResponse(
                original_query=query,
                doc_id=None,
                status="abstained",
                final_answer="I couldn't find enough evidence in the currently selected document to answer this question.",
                structured_answer=StructuredAnswer(
                    answer_type="abstention",
                    direct_answer="No document selected or indexed.",
                    evidence=[],
                ),
                citations=[],
                synthesis_method="abstained",
                verification_verdict="approved",
                verification_method="none",
                hallucination_ratio=0.0,
                sentence_verdicts=[],
                revision_suggestions=[],
                retry_count=0,
                abstained=True,
                abstain_reason="No document selected or indexed.",
            )

        # Check document-scoped cache
        if effective_doc_id:
            cached_data = await cache_service.get_cached("synthesis", effective_doc_id, query)
            if cached_data:
                logger.info(f"[CACHE HIT] Returning synthesis for doc_id={effective_doc_id!r} query={query!r}")
                return SynthesisResponse(**cached_data)

        try:
            if trust_report is None:
                trust_report = compute_trust_report(query=query, k=k, doc_id=effective_doc_id)
            final_state = run_full_pipeline(query, trust_report, max_retries=max_retries, doc_id=effective_doc_id)
        except Exception as exc:
            raise ServiceUnavailableError(f"Synthesis pipeline failed: {exc}") from exc

        report = final_state["final_report"]

        q_type = classify_query_type(query)
        retrieved_doc_ids = list({c.get("doc_id") for c in report.get("citations", []) if c.get("doc_id")})
        retrieved_chunk_ids = [c.get("chunk_id") for c in report.get("citations", [])]

        logger.info(
            f"\n========================================\n"
            f"QUESTION:\n{query}\n\n"
            f"TYPE:\n{q_type}\n\n"
            f"ACTIVE DOCUMENT ID:\n{effective_doc_id}\n\n"
            f"RETRIEVED DOCUMENT IDS:\n{retrieved_doc_ids}\n\n"
            f"RETRIEVED CHUNK IDS:\n{retrieved_chunk_ids}\n\n"
            f"OTHER DOCUMENTS:\nNONE\n\n"
            f"VERIFICATION RESULT:\n{report['verification_verdict']}\n"
            f"========================================"
        )

        struct_raw = report.get("structured_answer")
        structured_ans = None
        if struct_raw:
            try:
                structured_ans = StructuredAnswer(**struct_raw)
            except Exception as e:
                logger.warning(f"Could not parse structured_answer: {e}")

        response = SynthesisResponse(
            original_query=report["original_query"],
            doc_id=effective_doc_id,
            status=report["status"],
            final_answer=report["final_answer"],
            structured_answer=structured_ans,
            citations=[CitationResponse(**c) for c in report["citations"]],
            synthesis_method=report["synthesis_method"],
            verification_verdict=report["verification_verdict"],
            verification_method=report["verification_method"],
            hallucination_ratio=report["hallucination_ratio"],
            sentence_verdicts=[SentenceVerdictResponse(**v) for v in report["sentence_verdicts"]],
            revision_suggestions=report["revision_suggestions"],
            retry_count=report["retry_count"],
            abstained=report["abstained"],
            abstain_reason=report["abstain_reason"],
        )

        if effective_doc_id:
            await cache_service.set_cached("synthesis", effective_doc_id, query, response.model_dump())

        return response


_service_singleton: Optional[SynthesisService] = None


def get_synthesis_service() -> SynthesisService:
    global _service_singleton
    if _service_singleton is None:
        _service_singleton = SynthesisService()
    return _service_singleton
