"""
Node 3 — Search Multiple Queries with Document Scoping.

Runs every sub-query against the FAISS-backed retrieval pipeline with
candidate over-fetching and strict document ID scoping.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List

from loguru import logger

from agents.state.retriever_state import RetrieverState, SubQueryResult
from retrieval.retriever import get_retrieval_pipeline

PER_SUBQUERY_K_MULTIPLIER = 4
MIN_CANDIDATES_PER_SUBQUERY = 12


def search_multiple_queries(state: RetrieverState) -> Dict[str, Any]:
    """LangGraph node: reads `sub_queries`, `k`, and `doc_id`, writes `raw_results`."""
    pipeline = get_retrieval_pipeline()
    requested_k = state.get("k", 5)
    doc_id = state.get("doc_id")
    per_query_k = max(requested_k * PER_SUBQUERY_K_MULTIPLIER, MIN_CANDIDATES_PER_SUBQUERY)

    raw_results: List[SubQueryResult] = []
    for sub_query in state.get("sub_queries", []):
        chunks = pipeline.search(sub_query, k=per_query_k, doc_id=doc_id)
        chunk_dicts = [asdict(c) for c in chunks]
        raw_results.append({"sub_query": sub_query, "chunks": chunk_dicts})
        logger.info(
            f"[RETRIEVAL] Sub-query '{sub_query}' (doc_id={doc_id!r}) returned {len(chunk_dicts)} candidate chunk(s)."
        )

    return {"raw_results": raw_results}
