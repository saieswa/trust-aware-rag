"""
Node 3 — Search Multiple Queries.

Runs every sub-query from Node 2 against the FAISS-backed retrieval
pipeline built in the previous step (retrieval/retriever.py), independently.
Each sub-query gets its own top-k search — merging/deduplication happens
in later nodes, deliberately kept separate so this node's only job is
"go fetch candidates," nothing more.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List

from loguru import logger

from agents.state.retriever_state import RetrieverState, SubQueryResult
from retrieval.retriever import get_retrieval_pipeline

# Multiplier applied to the caller's requested k for each individual
# sub-query search. We deliberately over-fetch per sub-query (e.g. ask for
# 2x) because merging + deduplication in later nodes will collapse
# overlapping results — better to have a few extra candidates to rank from
# than to under-fetch and miss something.
PER_SUBQUERY_K_MULTIPLIER = 2


def search_multiple_queries(state: RetrieverState) -> Dict[str, Any]:
    """LangGraph node: reads `sub_queries` + `k`, writes `raw_results`."""
    pipeline = get_retrieval_pipeline()
    requested_k = state.get("k", 5)
    per_query_k = max(requested_k * PER_SUBQUERY_K_MULTIPLIER, requested_k)

    raw_results: List[SubQueryResult] = []
    for sub_query in state["sub_queries"]:
        chunks = pipeline.search(sub_query, k=per_query_k)
        chunk_dicts = [asdict(c) for c in chunks]
        raw_results.append({"sub_query": sub_query, "chunks": chunk_dicts})
        logger.info(f"Sub-query '{sub_query}' returned {len(chunk_dicts)} chunk(s).")

    return {"raw_results": raw_results}
