"""
Node 1 — Query Analysis.

Before deciding *how* to search, we first decide *whether* the question is
simple enough to search as-is, or complex enough to need splitting into
multiple focused queries. This is a fast, deterministic, rule-based check
— no LLM call — so every query pays a near-zero cost here before we decide
whether the (slower, optional) LLM decomposition step is even worth calling.

This mirrors how a human researcher skims a question first ("oh, this is
really two questions in one") before deciding how to go looking for
answers.
"""

from __future__ import annotations

from typing import Any, Dict

from loguru import logger

from agents.state.retriever_state import RetrieverState

# Words that typically signal "this question has more than one part."
CONJUNCTION_MARKERS = (" and ", " as well as ", " along with ")
COMPARISON_MARKERS = (" vs ", " versus ", " compared to ", "difference between", "which is better")

LONG_QUERY_WORD_THRESHOLD = 20


def _detect_signals(query: str) -> Dict[str, Any]:
    """Pull out simple, explainable signals from the raw query text."""
    lowered = query.lower()
    return {
        "word_count": len(query.split()),
        "question_mark_count": query.count("?"),
        "has_conjunction": any(marker in lowered for marker in CONJUNCTION_MARKERS),
        "has_comparison": any(marker in lowered for marker in COMPARISON_MARKERS),
    }


def analyze_query(state: RetrieverState) -> Dict[str, Any]:
    """
    LangGraph node: reads `original_query`, writes `analysis`.

    The decomposition decision is intentionally conservative (biased toward
    "no decomposition needed") — over-splitting a simple question wastes an
    LLM call and can fragment an otherwise-precise search into vaguer
    pieces. We only flag decomposition when there's a concrete signal the
    question actually has multiple parts.
    """
    query = state["original_query"]
    signals = _detect_signals(query)

    needs_decomposition = (
        signals["has_conjunction"]
        or signals["has_comparison"]
        or signals["question_mark_count"] > 1
        or signals["word_count"] > LONG_QUERY_WORD_THRESHOLD
    )

    analysis = {
        "needs_decomposition": needs_decomposition,
        "signals": signals,
    }

    logger.info(f"Query analysis: needs_decomposition={needs_decomposition} signals={signals}")
    return {"analysis": analysis}
