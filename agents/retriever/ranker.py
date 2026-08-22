"""
Node 6 — Relevance Reranking, and Node 7 — Return Top Evidence.

Reranks candidate chunks by:
1. Base FAISS semantic cosine similarity score.
2. Cross-query agreement bonus (matched across multiple sub-queries).
3. Section relevance boost (e.g. boosting Abstract/Introduction for problem queries).
4. Penalizing noise (pure bibliographies, appendix prompts, and disconnected formulas).
5. Discarding irrelevant chunks below the minimum relevance floor.
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
    """Awards a relevance boost or penalty based on document section match."""
    q_lower = query.lower()
    section = (chunk.get("section") or chunk.get("metadata", {}).get("section", "")).lower()
    text = chunk.get("text", "").lower()
    page = chunk.get("page_number") or chunk.get("metadata", {}).get("page_number", 999)

    boost = 0.0

    # 1. Problem Statement / Objective / Research Gap / Motivation
    if any(term in q_lower for term in ["problem", "motivation", "objective", "gap", "challenge", "purpose", "aim", "goal"]):
        if any(s in section for s in ["abstract", "introduction", "problem statement", "motivation"]):
            boost += 0.15
        elif page in [1, 2]:
            boost += 0.10
        if "appendix" in section or "references" in section or page > 15:
            boost -= 0.15

    # 2. Methodology / Approach / Model / Algorithm
    elif any(term in q_lower for term in ["method", "approach", "framework", "architecture", "algorithm", "technique"]):
        if any(s in section for s in ["method", "approach", "architecture", "empirical", "model"]):
            boost += 0.15
        if "references" in section:
            boost -= 0.20

    # 3. Results / Findings / Performance / Evaluation
    elif any(term in q_lower for term in ["result", "finding", "performance", "accuracy", "benchmark", "evaluation"]):
        if any(s in section for s in ["experiment", "result", "evaluation", "finding"]):
            boost += 0.15

    # 4. Conclusion / Summary
    elif any(term in q_lower for term in ["conclusion", "summary", "takeaway"]):
        if any(s in section for s in ["conclusion", "summary"]):
            boost += 0.15
        elif any(s in section for s in ["abstract"]):
            boost += 0.08

    # 5. Limitations / Drawbacks
    elif any(term in q_lower for term in ["limitation", "drawback", "weakness"]):
        if any(s in section for s in ["limitation", "discussion"]):
            boost += 0.15

    # Universal Noise Penalties
    if "references" in section or text.startswith("references") or text.count("et al.") >= 4:
        boost -= 0.25

    if "instruction:" in text and "structured data:" in text:
        boost -= 0.20

    return boost


def rank_results(state: RetrieverState) -> Dict[str, Any]:
    results = state.get("deduplicated_results", [])
    query = state.get("original_query", "")

    ranked_results: List[Dict[str, Any]] = []

    for result in results:
        base_score = float(result.get("score", 0.0))
        agreement_count = len(result.get("matched_sub_queries", []))
        agreement_bonus = AGREEMENT_BONUS_PER_EXTRA_MATCH * max(agreement_count - 1, 0)
        section_boost = _compute_section_boost(query, result)

        final_score = round(max(min(base_score + agreement_bonus + section_boost, MAX_SCORE), 0.0), 4)
        result["final_rank_score"] = final_score
        result["section"] = result.get("section") or result.get("metadata", {}).get("section", "General")
        result["page_number"] = result.get("page_number") or result.get("metadata", {}).get("page_number")

        ranked_results.append(result)

    # Sort descending by final rank score
    ranked_results = sorted(ranked_results, key=lambda r: r["final_rank_score"], reverse=True)

    strong_results = [r for r in ranked_results if r["final_rank_score"] >= MIN_ACCEPTABLE_RELEVANCE]
    final_list = strong_results if strong_results else ranked_results

    logger.info(
        f"Reranked {len(ranked_results)} candidate chunks for query: {query!r}. "
        f"Top score={final_list[0]['final_rank_score'] if final_list else 0.0:.4f}"
    )
    return {"ranked_results": final_list}


def select_top_evidence(state: RetrieverState) -> Dict[str, Any]:
    k = state.get("k", 5)
    top_evidence: List[Dict[str, Any]] = state.get("ranked_results", [])[:k]
    logger.info(f"Selected top {len(top_evidence)} evidence chunks for Critic Agent.")
    return {"top_evidence": top_evidence}
