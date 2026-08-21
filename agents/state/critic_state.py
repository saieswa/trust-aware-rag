"""
Critic Agent — LangGraph State.

Input: the `original_query` plus the `evidence` list the Retriever Agent
already produced (top_evidence chunks: chunk_id, doc_id, text, score,
source_title, source_path, matched_sub_queries).

Output: `critic_report` — the single structured JSON object the
Synthesizer Agent (next project step) and, eventually, the Trust Model
will consume. Every intermediate stage is kept in state too, so the report
is fully auditable rather than a black box.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class CriticState(TypedDict, total=False):
    # ---------- Input ----------
    original_query: str
    evidence: List[Dict[str, Any]]

    # ---------- Stage 1: Read retrieved documents ----------
    normalized_evidence: List[Dict[str, Any]]

    # ---------- Stage 2 & 3: Quality + reliability scoring ----------
    quality_scores: Dict[str, Dict[str, Any]]  # keyed by chunk_id

    # ---------- Stage 4: Contradiction detection ----------
    contradictions: List[Dict[str, Any]]
    contradiction_method: str  # "llm" | "heuristic"

    # ---------- Stage 5: Support / Contradict / Neutral labeling ----------
    labels: Dict[str, Dict[str, Any]]  # keyed by chunk_id
    labeling_method: str  # "llm" | "heuristic"

    # ---------- Final structured output ----------
    critic_report: Dict[str, Any]

    # ---------- Diagnostics ----------
    error: Optional[str]
