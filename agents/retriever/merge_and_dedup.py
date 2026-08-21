"""
Node 4 — Merge Results, and Node 5 — Remove Duplicate Chunks.

Kept as two separate, small functions (rather than one "merge_and_dedup"
function) because they answer two different questions:

  merge_results()       — "put every sub-query's results into one flat list,
                           tracking which sub-quer(y/ies) surfaced each chunk"
  deduplicate_chunks()  — "the same chunk was often retrieved by more than
                           one sub-query — collapse it to a single entry"

Separating them means each is independently testable, and the "which
sub-queries matched this chunk" signal survives deduplication — it becomes
an agreement signal the ranker (Node 6) uses.
"""

from __future__ import annotations

from typing import Any, Dict, List

from loguru import logger

from agents.state.retriever_state import RetrieverState


def merge_results(state: RetrieverState) -> Dict[str, Any]:
    """
    LangGraph node: reads `raw_results`, writes `merged_results`.

    Flattens the per-sub-query results into one list. Each chunk gets a new
    `matched_sub_queries` field (a list, so far containing just the one
    sub-query that surfaced it) — deduplication merges these lists when the
    same chunk appears under multiple sub-queries.
    """
    merged: List[Dict[str, Any]] = []
    for entry in state["raw_results"]:
        sub_query = entry["sub_query"]
        for chunk in entry["chunks"]:
            merged.append({**chunk, "matched_sub_queries": [sub_query]})

    logger.info(f"Merged {len(state['raw_results'])} sub-query result set(s) into {len(merged)} chunk entries.")
    return {"merged_results": merged}


def deduplicate_chunks(state: RetrieverState) -> Dict[str, Any]:
    """
    LangGraph node: reads `merged_results`, writes `deduplicated_results`.

    Groups by `chunk_id` (the same chunk can legitimately be returned by
    more than one sub-query search). For each duplicate:
      - keeps the HIGHEST similarity score seen across sub-queries
        (whichever sub-query phrasing matched it best),
      - unions the `matched_sub_queries` lists, so a chunk that matched 2
        different sub-queries carries that fact into the ranking stage —
        a chunk that's relevant to multiple parts of the question is a
        stronger candidate than one that only matched one narrow phrasing.
    """
    deduped: Dict[str, Dict[str, Any]] = {}

    for item in state["merged_results"]:
        chunk_id = item["chunk_id"]
        if chunk_id not in deduped:
            deduped[chunk_id] = dict(item)
        else:
            existing = deduped[chunk_id]
            existing["score"] = max(existing["score"], item["score"])
            existing["matched_sub_queries"] = sorted(
                set(existing["matched_sub_queries"]) | set(item["matched_sub_queries"])
            )

    deduplicated_results = list(deduped.values())
    logger.info(
        f"Deduplicated {len(state['merged_results'])} entries down to "
        f"{len(deduplicated_results)} unique chunk(s)."
    )
    return {"deduplicated_results": deduplicated_results}
