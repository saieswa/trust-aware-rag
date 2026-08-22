"""
Retriever Agent — LangGraph State.

LangGraph passes a single state object through every node in the graph.
Includes `doc_id` to strictly scope search to the currently active document.
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
    k: int
    doc_id: Optional[str]  # Scopes retrieval exclusively to this document ID

    # ---------- Stage 1: Query Analysis ----------
    analysis: Dict[str, Any]

    # ---------- Stage 2: Query Decomposition ----------
    sub_queries: List[str]
    decomposition_method: str

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
