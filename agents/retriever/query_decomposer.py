"""
Node 2 — Query Decomposition.

If Node 1 decided the question doesn't need splitting, this is a no-op —
`sub_queries` becomes a single-item list containing the original query.

If it does need splitting, we ask an LLM (Groq, via LangChain) to produce
1-3 focused search queries. LLM calls can fail for all sorts of real-world
reasons — no API key configured, rate limits, network issues — so this is
wrapped to fall back to a deterministic heuristic splitter instead of
crashing the whole retrieval pipeline over a single unavailable API call.
That fallback matters in production: a temporary Groq outage should
degrade retrieval quality slightly, not take the feature down entirely.
"""

from __future__ import annotations

from typing import Any, Dict, List

from loguru import logger
from pydantic import BaseModel, Field

from agents.llm_client import get_groq_llm
from agents.prompts.retriever_prompts import (
    QUERY_DECOMPOSITION_SYSTEM_PROMPT,
    QUERY_DECOMPOSITION_USER_TEMPLATE,
)
from agents.state.retriever_state import RetrieverState

MAX_SUB_QUERIES = 3

# Fallback split markers, used only if the LLM call is unavailable.
_HEURISTIC_SPLIT_MARKERS = [" and ", " vs ", " versus ", " compared to "]


class SubQueryList(BaseModel):
    """Structured output schema the LLM is asked to fill in."""

    queries: List[str] = Field(
        description="1 to 3 focused search queries that together cover the original question."
    )


def _llm_decompose(query: str) -> List[str]:
    """
    ask Groq to decompose the query.

    Raises on any failure (missing API key, network error, malformed
    response) — the caller (`decompose_query`) is responsible for catching
    that and falling back to the heuristic splitter.
    """
    llm = get_groq_llm(temperature=0, timeout=15)
    structured_llm = llm.with_structured_output(SubQueryList)

    result = structured_llm.invoke(
        [
            ("system", QUERY_DECOMPOSITION_SYSTEM_PROMPT),
            ("human", QUERY_DECOMPOSITION_USER_TEMPLATE.format(query=query)),
        ]
    )
    return result.queries


def _heuristic_decompose(query: str) -> List[str]:
    """
    Deterministic fallback: split on common conjunction/comparison phrases.

    This won't be as semantically precise as an LLM, but it's dependency-free,
    instant, and guarantees the pipeline always produces *something*
    reasonable even with zero external services available.
    """
    lowered = query.lower()
    for marker in _HEURISTIC_SPLIT_MARKERS:
        if marker in lowered:
            parts = [p.strip(" ?.") for p in query.split(marker.strip())]
            parts = [p for p in parts if len(p.split()) >= 2]  # drop fragments too short to search on
            if len(parts) >= 2:
                return parts
    # No recognizable split point — just search the whole question as-is.
    return [query]


def _clean_sub_queries(sub_queries: List[str], original_query: str) -> List[str]:
    """De-duplicate (case-insensitive), drop empties, cap at MAX_SUB_QUERIES,
    and guarantee we never return zero queries."""
    seen = set()
    cleaned: List[str] = []
    for q in sub_queries:
        q = q.strip()
        key = q.lower()
        if q and key not in seen:
            seen.add(key)
            cleaned.append(q)
        if len(cleaned) == MAX_SUB_QUERIES:
            break
    return cleaned or [original_query]


def decompose_query(state: RetrieverState) -> Dict[str, Any]:
    """LangGraph node: reads `original_query` + `analysis`, writes `sub_queries`
    and `decomposition_method` (useful for debugging/observability — you can
    see in logs/response whether a given answer used the LLM or the fallback)."""
    query = state["original_query"]
    analysis = state["analysis"]

    if not analysis["needs_decomposition"]:
        logger.info("Decomposition skipped — query analysis judged this a single-topic question.")
        return {"sub_queries": [query], "decomposition_method": "none"}

    try:
        sub_queries = _llm_decompose(query)
        method = "llm"
    except Exception as exc:
        logger.warning(f"LLM decomposition unavailable ({exc}); falling back to heuristic split.")
        sub_queries = _heuristic_decompose(query)
        method = "heuristic"

    sub_queries = _clean_sub_queries(sub_queries, query)
    logger.info(f"Decomposed query into {len(sub_queries)} sub-quer(y/ies) via {method}: {sub_queries}")
    return {"sub_queries": sub_queries, "decomposition_method": method}
