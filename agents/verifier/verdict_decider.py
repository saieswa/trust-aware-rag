"""
Verifier Node 3 — Decide Verdict (Reject Hallucinations).

Turns the per-sentence verdicts into one pipeline-level decision:
"approved" or "rejected". Rejection happens when the hallucination ratio
clears a threshold — a single borderline sentence shouldn't throw away an
otherwise-solid answer, but a draft where a meaningful fraction of claims
aren't grounded should never reach the user as-is.

`revision_suggestions` is the concrete, actionable list the retry loop
(agents/pipeline/agent.py) feeds back into the Synthesizer's next attempt
— this is what turns "rejected" into "rejected, and here's exactly what to
fix," rather than a dead end.
"""

from __future__ import annotations

from typing import Any, Dict

from loguru import logger

from agents.state.synthesis_state import SynthesisVerificationState

# Above this fraction of unsupported sentences, the draft is rejected
# outright rather than accepted with caveats.
HALLUCINATION_REJECTION_THRESHOLD = 0.2


def decide_verdict(state: SynthesisVerificationState) -> Dict[str, Any]:
    """LangGraph node: reads `hallucination_ratio`, `sentence_verdicts`;
    writes `verification_verdict`, `revision_suggestions`."""
    if state.get("abstained"):
        return {"verification_verdict": "approved", "revision_suggestions": []}

    hallucination_ratio = state.get("hallucination_ratio", 0.0)
    verdicts = state.get("sentence_verdicts", [])

    if hallucination_ratio > HALLUCINATION_REJECTION_THRESHOLD:
        suggestions = [
            f"\"{v['sentence']}\" — {v['suggestion']}"
            for v in verdicts
            if v["verdict"] == "unsupported"
        ]
        logger.warning(
            f"Verifier REJECTED draft — hallucination_ratio={hallucination_ratio} "
            f"exceeds threshold {HALLUCINATION_REJECTION_THRESHOLD}."
        )
        return {"verification_verdict": "rejected", "revision_suggestions": suggestions}

    logger.info(f"Verifier APPROVED draft — hallucination_ratio={hallucination_ratio}.")
    return {"verification_verdict": "approved", "revision_suggestions": []}
