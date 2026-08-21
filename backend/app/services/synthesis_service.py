"""
Synthesis Service.

If the caller already has a trust_report (e.g. from a prior /trust/score
call), synthesis runs directly against it. Otherwise, this computes one
first — running the full Retriever -> Critic -> Trust chain — so a single
API call can go from a raw question to a verified, citation-backed answer.
"""

from typing import Any, Dict, Optional

from app.core.exceptions import ServiceUnavailableError
from app.schemas.synthesis import CitationResponse, SentenceVerdictResponse, SynthesisResponse
from agents.pipeline.agent import run_full_pipeline
from trust.trust_engine import compute_trust_report


class SynthesisService:
    def run(
        self, query: str, k: int, max_retries: int, trust_report: Optional[Dict[str, Any]]
    ) -> SynthesisResponse:
        try:
            if trust_report is None:
                trust_report = compute_trust_report(query=query, k=k)
            final_state = run_full_pipeline(query, trust_report, max_retries=max_retries)
        except Exception as exc:
            raise ServiceUnavailableError(f"Synthesis pipeline failed: {exc}") from exc

        report = final_state["final_report"]

        return SynthesisResponse(
            original_query=report["original_query"],
            status=report["status"],
            final_answer=report["final_answer"],
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


_service_singleton: Optional[SynthesisService] = None


def get_synthesis_service() -> SynthesisService:
    global _service_singleton
    if _service_singleton is None:
        _service_singleton = SynthesisService()
    return _service_singleton
