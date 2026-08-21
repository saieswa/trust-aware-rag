"""
Synthesizer Node 1 — Select Verified Evidence.

This is what makes the Synthesizer "use only verified evidence" a real
guarantee rather than a prompt instruction alone: chunks the Critic Agent
labeled "contradict" or "neutral" are filtered out here, in code, before
the LLM ever sees them — the model physically cannot cite evidence it was
never given.

This node also makes the abstention decision. Two independent reasons can
trigger it:
  1. The Trust Score system already decided "abstain" (trust_report.decision).
  2. Even if trust wasn's that low, there's simply zero "support" evidence
     to write from — no evidence to synthesize from means nothing to say.
"""

from __future__ import annotations

from typing import Any, Dict

from loguru import logger

from agents.state.synthesis_state import SynthesisVerificationState


def select_verified_evidence(state: SynthesisVerificationState) -> Dict[str, Any]:
    """LangGraph node: reads `trust_report`, writes `verified_evidence`,
    `abstained`, `abstain_reason`."""
    trust_report = state["trust_report"]
    all_evidence = trust_report.get("evidence", [])

    verified_evidence = [e for e in all_evidence if e.get("label") == "support"]
    # Highest-quality evidence first, so if we ever truncate (not done yet,
    # but a natural future guardrail against prompt-size limits), we keep
    # the strongest chunks.
    verified_evidence.sort(key=lambda e: e.get("quality_score", 0.0), reverse=True)

    if trust_report.get("decision") == "abstain":
        logger.info("Synthesizer: trust score decision is 'abstain' — skipping synthesis.")
        return {
            "verified_evidence": verified_evidence,
            "abstained": True,
            "abstain_reason": (
                f"Trust score ({trust_report.get('trust_score')}) was below the abstention "
                f"threshold — evidence was not reliable/consistent enough to answer confidently."
            ),
        }

    if not verified_evidence:
        logger.info("Synthesizer: no 'support'-labeled evidence available — skipping synthesis.")
        return {
            "verified_evidence": [],
            "abstained": True,
            "abstain_reason": "No verified (non-contradicted, sufficiently reliable) evidence was found for this question.",
        }

    logger.info(f"Synthesizer: {len(verified_evidence)} verified evidence chunk(s) selected.")
    return {"verified_evidence": verified_evidence, "abstained": False, "abstain_reason": None}
