"""
Retriever Agent — LangGraph State.

LangGraph passes a single state object through every node in the graph;
each node reads whatever keys it needs and returns a dict of the keys it's
adding/updating (LangGraph merges that into the running state — it does
not require every node to return the whole state).

Defining this as one TypedDict, in one place, means every node function
below has a single source of truth for what's available at each stage of
the pipeline, and Section 8's API layer can type-check against exactly the
same shape.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class SubQueryResult(TypedDict):
    """Raw search results for one decomposed sub-query, before merging."""

    sub_query: str
    chunks: List[Dict[str, Any]]


class RetrieverState(TypedDict, total=False):
    # ---------- Input ----------
    original_query: str
    k: int  # how many top chunks the caller ultimately wants

    # ---------- Stage 1: Query Analysis ----------
    analysis: Dict[str, Any]

    # ---------- Stage 2: Query Decomposition ----------
    sub_queries: List[str]
    decomposition_method: str  # "llm" | "heuristic" | "none" — for transparency/debugging

    # ---------- Stage 3: Multi-query search ----------
    raw_results: List[SubQueryResult]

    # ---------- Stage 4: Merge ----------
    merged_results: List[Dict[str, Any]]

    # ---------- Stage 5: Deduplication ----------
    deduplicated_results: List[Dict[str, Any]]

    # ---------- Stage 6: Ranking ----------
    ranked_results: List[Dict[str, Any]]

    # ---------- Stage 7: Final output ----------
    top_evidence: List[Dict[str, Any]]

    # ---------- Diagnostics ----------
    error: Optional[str]
