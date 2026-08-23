"""
Node 1 — Query Analysis and Query Routing.

Detects query complexity and classifies the question intent into:
1. DOCUMENT_LEVEL: Broad summary, overview, purpose, or explanation of the entire document
   (e.g., 'Can you explain this PDF?', 'Summarize this document', 'What is this paper about?').
2. SPECIFIC: Focused factual questions targeting algorithms, definitions, authors, results, etc.
"""

from __future__ import annotations

import re
from typing import Any, Dict

from loguru import logger

from agents.state.retriever_state import RetrieverState

# Words that typically signal "this question has more than one part."
CONJUNCTION_MARKERS = (" and ", " as well as ", " along with ")
COMPARISON_MARKERS = (" vs ", " versus ", " compared to ", "difference between", "which is better")

LONG_QUERY_WORD_THRESHOLD = 20

DOCUMENT_LEVEL_PATTERNS = [
    re.compile(r"\b(?:explain|walk\s+me\s+through|break\s+down|tell\s+me\s+about|clarify|elaborate\s+on)\s+(?:this|the|entire)?\s*(?:pdf|document|paper|file|text|study|article|work)\b", re.I),
    re.compile(r"\b(?:summarize|summarise|summary\s+of|give\s+(?:me\s+)?(?:a\s+|an\s+)?summary|overview\s+of|give\s+(?:me\s+)?(?:a\s+|an\s+)?overview)\s*(?:of)?\s*(?:this|the)?\s*(?:pdf|document|paper|file|study|article)?\b", re.I),
    re.compile(r"\bwhat\s+(?:is|does)\s+(?:this|the)\s+(?:paper|document|pdf|article|file|study|work)\s+(?:about|discuss|describe|cover|say|talk\s+about)\b", re.I),
    re.compile(r"\bwhat\s+are\s+the\s+(?:main|key|core|central)\s+(?:ideas|findings|takeaways|points|contributions|topics|themes)\b", re.I),
    re.compile(r"\bwhat\s+is\s+the\s+(?:main\s+)?purpose\s+of\s+(?:this|the)\s+(?:paper|document|pdf|study|work)\b", re.I),
    re.compile(r"\bcan\s+you\s+(?:please\s+)?(?:explain|summarize|break\s+down|walk\s+through)\s+(?:this|the)?\s*(?:pdf|document|paper|file)\b", re.I),
    re.compile(r"\bexplain\s+(?:the\s+)?entire\s+(?:paper|document|pdf|work)\b", re.I),
    re.compile(r"^(?:explain|summarize|summary|overview|breakdown)\s*(?:this|the)?\s*(?:pdf|document|paper)?\??$", re.I),
]


def classify_query_type(query: str) -> str:
    """Classifies a query as DOCUMENT_LEVEL or SPECIFIC."""
    q_trimmed = query.strip()
    for pattern in DOCUMENT_LEVEL_PATTERNS:
        if pattern.search(q_trimmed):
            return "DOCUMENT_LEVEL"
    return "SPECIFIC"


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
    LangGraph node: reads `original_query`, writes `analysis` and `query_type`.
    """
    query = state["original_query"]
    signals = _detect_signals(query)
    query_type = classify_query_type(query)

    needs_decomposition = (
        query_type == "SPECIFIC"
        and (
            signals["has_conjunction"]
            or signals["has_comparison"]
            or signals["question_mark_count"] > 1
            or signals["word_count"] > LONG_QUERY_WORD_THRESHOLD
        )
    )

    analysis = {
        "needs_decomposition": needs_decomposition,
        "signals": signals,
        "query_type": query_type,
    }

    logger.info(f"Query analysis: query_type={query_type} needs_decomposition={needs_decomposition} signals={signals}")
    return {"analysis": analysis, "query_type": query_type}
