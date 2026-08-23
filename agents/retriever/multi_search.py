"""
Node 3 — Search Multiple Queries with Document Scoping and Document-Level Routing.

Runs document-level extraction or sub-query semantic vector searches strictly scoped to doc_id.
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
    """LangGraph node: reads `sub_queries`, `k`, `doc_id`, and `query_type`, writes `raw_results`."""
    pipeline = get_retrieval_pipeline()
    requested_k = state.get("k", 5)
    doc_id = state.get("doc_id")
    query_type = state.get("query_type", "SPECIFIC")

    raw_results: List[SubQueryResult] = []

    if query_type == "DOCUMENT_LEVEL" and doc_id:
        doc_chunks = pipeline.get_document_chunks(doc_id, max_chunks=15)
        chunk_dicts = [asdict(c) for c in doc_chunks]
        raw_results.append({
            "sub_query": state.get("original_query", ""),
            "chunks": chunk_dicts,
        })
        logger.info(
            f"[RETRIEVAL] DOCUMENT_LEVEL query routed to direct document extraction: "
            f"{len(chunk_dicts)} chunks retrieved for doc_id={doc_id!r}."
        )
        return {"raw_results": raw_results}

    per_query_k = max(requested_k * PER_SUBQUERY_K_MULTIPLIER, MIN_CANDIDATES_PER_SUBQUERY)
    for sub_query in state.get("sub_queries", []):
        chunks = pipeline.search(sub_query, k=per_query_k, doc_id=doc_id)
        chunk_dicts = [asdict(c) for c in chunks]
        raw_results.append({"sub_query": sub_query, "chunks": chunk_dicts})
        logger.info(
            f"[RETRIEVAL] Sub-query '{sub_query}' (doc_id={doc_id!r}) returned {len(chunk_dicts)} candidate chunk(s)."
        )

    return {"raw_results": raw_results}
