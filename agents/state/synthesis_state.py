"""
Synthesizer + Verifier — Shared LangGraph State.

These two agents are tightly coupled by design: the Verifier's job is to
check the Synthesizer's output sentence-by-sentence, and — if it finds
unsupported claims — send it back with concrete revision feedback for a
second attempt. That feedback loop is the reason they share one state
schema and one graph (see agents/pipeline/agent.py) rather than being two
fully independent pipelines: the loop needs to carry `revision_feedback`
from the Verifier back into the Synthesizer's next attempt.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class SynthesisVerificationState(TypedDict, total=False):
    # ---------- Input ----------
    original_query: str
    trust_report: Dict[str, Any]  # output of trust/trust_engine.py
    max_retries: int

    # ---------- Synthesizer: evidence selection ----------
    verified_evidence: List[Dict[str, Any]]
    abstained: bool
    abstain_reason: Optional[str]

    # ---------- Synthesizer: drafting ----------
    draft_answer: str
    citations: List[Dict[str, Any]]
    synthesis_method: str  # "llm" | "heuristic" | "abstained"
    revision_feedback: Optional[str]  # set by the Verifier, read on retry

    # ---------- Verifier: sentence-level checking ----------
    sentences: List[str]
    sentence_verdicts: List[Dict[str, Any]]
    hallucination_ratio: float
    verification_verdict: str  # "approved" | "rejected"
    revision_suggestions: List[str]
    verification_method: str  # "llm" | "heuristic"

    # ---------- Loop control ----------
    retry_count: int

    # ---------- Final output ----------
    final_report: Dict[str, Any]
