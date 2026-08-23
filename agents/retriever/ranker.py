"""
Node 6 — Relevance Reranking with Title/Metadata Boost and Document Scope Filtering.

Reranks candidate chunks by:
1. Strict document ID scoping (drops any chunk not belonging to the active doc_id).
2. Base FAISS semantic cosine similarity score (or sequential document preservation for DOCUMENT_LEVEL).
3. Cross-query agreement bonus.
4. Section & Page relevance boost.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from loguru import logger
from agents.state.retriever_state import RetrieverState

AGREEMENT_BONUS_PER_EXTRA_MATCH = 0.05
MIN_ACCEPTABLE_RELEVANCE = 0.20
MAX_SCORE = 1.0


def _compute_section_boost(query: str, chunk: Dict[str, Any]) -> float:
    """Awards a relevance boost or penalty based on document section & page match."""
    q_lower = query.lower()
    section = (chunk.get("section") or chunk.get("metadata", {}).get("section", "")).lower()
    text = chunk.get("text", "").lower()
    page = chunk.get("page_number") or chunk.get("metadata", {}).get("page_number", 999)
    chunk_idx = chunk.get("chunk_index", 999)

    boost = 0.0

    # 0. Title / Author Identity Queries (Prioritize Page 1 & first chunk)
    if any(term in q_lower for term in ["title of this", "title of the", "name of this paper", "who are the authors", "who wrote this", "who authored", "authors of this"]):
        if page == 1 or chunk_idx == 0:
            boost += 0.35
        elif any(s in section for s in ["abstract", "introduction"]):
            boost += 0.20
        if "appendix" in section or page > 5:
            boost -= 0.30

    # 1. Problem Statement / Objective / Research Gap / Motivation
    elif any(term in q_lower for term in ["problem", "motivation", "objective", "gap", "challenge", "purpose", "aim", "goal"]):
        if any(s in section for s in ["abstract", "introduction", "problem statement", "motivation"]):
            boost += 0.30
        elif page in [1, 2] or chunk_idx in [0, 1]:
            boost += 0.25
        if "appendix" in section or "references" in section or page > 15:
            boost -= 0.20

    # 2. Methodology / Approach / Model / Algorithm
    elif any(term in q_lower for term in ["method", "approach", "framework", "architecture", "algorithm", "technique"]):
        if any(s in section for s in ["method", "approach", "architecture", "empirical", "model"]):
            boost += 0.25
        if "references" in section:
            boost -= 0.20

    # 3. Results / Findings / Performance / Evaluation
    elif any(term in q_lower for term in ["result", "finding", "performance", "accuracy", "benchmark", "evaluation"]):
        if any(s in section for s in ["experiment", "result", "evaluation", "finding"]):
            boost += 0.30
        else:
            boost += 0.22

    # 4. Conclusion / Summary
    elif any(term in q_lower for term in ["conclusion", "summary", "takeaway"]):
        if any(s in section for s in ["conclusion", "summary"]):
            boost += 0.20
        elif any(s in section for s in ["abstract"]):
            boost += 0.10

    # 5. Limitations / Drawbacks
    elif any(term in q_lower for term in ["limitation", "drawback", "weakness"]):
        if any(s in section for s in ["limitation", "discussion"]):
            boost += 0.20

    # Universal Noise Penalties
    if "references" in section or text.startswith("references") or text.count("et al.") >= 4:
        boost -= 0.25

    if "instruction:" in text and "structured data:" in text:
        boost -= 0.20

    return boost


def rank_results(state: RetrieverState) -> Dict[str, Any]:
    results = state.get("deduplicated_results", [])
    query = state.get("original_query", "")
    target_doc_id = state.get("doc_id")
    query_type = state.get("query_type", "SPECIFIC")

    ranked_results: List[Dict[str, Any]] = []

    for result in results:
        # Enforce document ID isolation
        chunk_doc_id = result.get("doc_id") or result.get("metadata", {}).get("doc_id")
        if target_doc_id and chunk_doc_id and chunk_doc_id != target_doc_id:
            logger.warning(
                f"[RETRIEVAL] Dropping chunk {result.get('chunk_id')} from wrong document: {chunk_doc_id} != {target_doc_id}"
            )
            continue

        base_score = float(result.get("score", 0.0))
        agreement_count = len(result.get("matched_sub_queries", []))
        agreement_bonus = AGREEMENT_BONUS_PER_EXTRA_MATCH * max(agreement_count - 1, 0)
        section_boost = _compute_section_boost(query, result)

        if query_type == "DOCUMENT_LEVEL":
            final_score = round(max(base_score, 0.88), 4)
        else:
            final_score = round(max(min(base_score + agreement_bonus + section_boost, MAX_SCORE), 0.0), 4)

        result["final_rank_score"] = final_score
        result["section"] = result.get("section") or result.get("metadata", {}).get("section", "General")
        result["page_number"] = result.get("page_number") or result.get("metadata", {}).get("page_number")

        ranked_results.append(result)

    if query_type == "DOCUMENT_LEVEL":
        ranked_results.sort(key=lambda r: (r.get("page_number") or 1, r.get("chunk_index") or 0))
        final_list = ranked_results
    else:
        ranked_results.sort(key=lambda r: r["final_rank_score"], reverse=True)
        strong_results = [r for r in ranked_results if r["final_rank_score"] >= MIN_ACCEPTABLE_RELEVANCE]
        final_list = strong_results if strong_results else ranked_results

    logger.info(
        f"[RETRIEVAL] Reranked {len(ranked_results)} candidate chunks for query: {query!r} (type={query_type}, doc_id={target_doc_id!r}). "
        f"Top score={final_list[0]['final_rank_score'] if final_list else 0.0:.4f}"
    )
    return {"ranked_results": final_list}


def select_top_evidence(state: RetrieverState) -> Dict[str, Any]:
    k = state.get("k", 5)
    query_type = state.get("query_type", "SPECIFIC")
    all_ranked = state.get("ranked_results", [])

    if query_type == "DOCUMENT_LEVEL":
        top_evidence: List[Dict[str, Any]] = all_ranked[:12]
    else:
        top_evidence = all_ranked[:k]

    logger.info(f"[RETRIEVAL] Selected top {len(top_evidence)} evidence chunks for Critic Agent (type={query_type}).")
    return {"top_evidence": top_evidence}
