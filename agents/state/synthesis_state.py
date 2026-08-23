"""
Synthesizer + Verifier — Shared LangGraph State.

These two agents are tightly coupled by design: the Verifier's job is to
check the Synthesizer's output sentence-by-sentence, and — if it finds
unsupported claims — send it back with concrete revision feedback for a
second attempt.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class SynthesisVerificationState(TypedDict, total=False):
    # ---------- Input ----------
    original_query: str
    trust_report: Dict[str, Any]  # output of trust/trust_engine.py
    max_retries: int
    doc_id: Optional[str]  # Scoped active document ID

    # ---------- Synthesizer: evidence selection ----------
    verified_evidence: List[Dict[str, Any]]
    abstained: bool
    abstain_reason: Optional[str]

    # ---------- Synthesizer: drafting ----------
    draft_answer: str
    structured_answer: Optional[Dict[str, Any]]
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
