"""
Pipeline Final Node — Finalize Response.
"""

from __future__ import annotations

from typing import Any, Dict

from loguru import logger

from agents.state.synthesis_state import SynthesisVerificationState


def finalize_response(state: SynthesisVerificationState) -> Dict[str, Any]:
    """LangGraph node: reads the full pipeline state, writes `final_report`."""
    verdict = state.get("verification_verdict", "approved")
    retries_exhausted = state.get("retry_count", 0) >= state.get("max_retries", 2) and verdict == "rejected"

    if state.get("abstained"):
        final_answer = state["draft_answer"]
        status = "abstained"
    elif retries_exhausted:
        final_answer = (
            "I wasn't able to produce an answer fully supported by the evidence after "
            "multiple attempts, so I'm not confident enough to answer this directly. "
            "The closest attempt contains claims that couldn't be verified against the active document."
        )
        status = "verification_failed"
    else:
        final_answer = state["draft_answer"]
        status = "approved"

    report = {
        "original_query": state["original_query"],
        "status": status,
        "final_answer": final_answer,
        "structured_answer": state.get("structured_answer"),
        "last_draft_answer": state.get("draft_answer"),
        "citations": state.get("citations", []),
        "synthesis_method": state.get("synthesis_method", "none"),
        "verification_verdict": verdict,
        "verification_method": state.get("verification_method", "none"),
        "hallucination_ratio": state.get("hallucination_ratio", 0.0),
        "sentence_verdicts": state.get("sentence_verdicts", []),
        "revision_suggestions": state.get("revision_suggestions", []),
        "retry_count": state.get("retry_count", 0),
        "abstained": state.get("abstained", False),
        "abstain_reason": state.get("abstain_reason"),
    }

    logger.info(
        f"Pipeline finalized — status={status} retries={report['retry_count']} "
        f"verdict={verdict}"
    )
    return {"final_report": report}
