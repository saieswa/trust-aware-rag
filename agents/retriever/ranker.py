"""
Node 6 — Rank Results, and Node 7 — Return Top Evidence.

Ranking combines two signals into one `final_rank_score`:
  1. The raw similarity score from FAISS (how close the chunk's meaning is
     to whichever sub-query found it).
  2. An "agreement bonus" — a chunk found by more than one sub-query is
     more likely to be broadly relevant to the *whole* question, not just
     one narrow phrasing of it, so it gets a small score boost per extra
     sub-query match.

This agreement signal is a direct preview of the trust-scoring idea from
the project's design docs: multiple independent retrieval paths agreeing
on a chunk is itself a (weak) trust signal, well before the Critic Agent
does any deeper judgment on it.
"""

from __future__ import annotations

from typing import Any, Dict, List

from loguru import logger

from agents.state.retriever_state import RetrieverState

# How much score to add per additional sub-query that matched the same chunk.
# Kept small and capped (see rank_results) so agreement can nudge ranking,
# not completely override actual semantic similarity.
AGREEMENT_BONUS_PER_EXTRA_MATCH = 0.03
MAX_SCORE = 1.0


def rank_results(state: RetrieverState) -> Dict[str, Any]:
    """LangGraph node: reads `deduplicated_results`, writes `ranked_results`."""
    results = state["deduplicated_results"]

    for result in results:
        agreement_count = len(result["matched_sub_queries"])
        agreement_bonus = AGREEMENT_BONUS_PER_EXTRA_MATCH * max(agreement_count - 1, 0)
        result["final_rank_score"] = round(min(result["score"] + agreement_bonus, MAX_SCORE), 4)

    ranked_results = sorted(results, key=lambda r: r["final_rank_score"], reverse=True)
    logger.info(f"Ranked {len(ranked_results)} chunk(s) by similarity + agreement bonus.")
    return {"ranked_results": ranked_results}


def select_top_evidence(state: RetrieverState) -> Dict[str, Any]:
    """
    LangGraph node: reads `ranked_results` + `k`, writes `top_evidence`.

    This is the final output of the Retriever Agent — the exact list of
    chunks the Critic Agent (next project step) will receive and judge.
    """
    k = state.get("k", 5)
    top_evidence: List[Dict[str, Any]] = state["ranked_results"][:k]
    logger.info(f"Selected top {len(top_evidence)} evidence chunk(s) (requested k={k}).")
    return {"top_evidence": top_evidence}
