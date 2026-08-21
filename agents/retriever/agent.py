"""
Retriever Agent — Graph Assembly.

Wires the seven nodes (query_analyzer, query_decomposer, multi_search,
merge_and_dedup x2, ranker x2) into a single linear LangGraph pipeline, and
exposes one function — `run_retriever_agent()` — as the public entrypoint
everything else in the app calls. Nothing outside this file needs to know
LangGraph is even involved.

    ┌────────────────┐
    │ analyze_query   │   Node 1 — decide if the question needs splitting
    └───────┬────────┘
            ▼
    ┌────────────────┐
    │ decompose_query │   Node 2 — LLM (or heuristic fallback) splits it
    └───────┬────────┘
            ▼
    ┌──────────────────────┐
    │ search_multiple_      │  Node 3 — FAISS search, once per sub-query
    │ queries               │
    └───────┬──────────────┘
            ▼
    ┌────────────────┐
    │ merge_results   │   Node 4 — flatten all sub-query results into one list
    └───────┬────────┘
            ▼
    ┌────────────────────┐
    │ deduplicate_chunks  │  Node 5 — collapse repeated chunks, keep best score
    └───────┬────────────┘
            ▼
    ┌────────────────┐
    │ rank_results    │   Node 6 — similarity + cross-query agreement bonus
    └───────┬────────┘
            ▼
    ┌────────────────────┐
    │ select_top_evidence │  Node 7 — truncate to the requested top-k
    └────────────────────┘

The graph is linear (no branching/looping) at this stage — branching (e.g.
"if trust is low, loop back to search with a wider net") is introduced once
the Critic Agent and trust score exist in a later step.
"""

from __future__ import annotations

from typing import Any, Dict

from langgraph.graph import END, START, StateGraph
from loguru import logger

from agents.retriever.merge_and_dedup import deduplicate_chunks, merge_results
from agents.retriever.multi_search import search_multiple_queries
from agents.retriever.query_analyzer import analyze_query
from agents.retriever.query_decomposer import decompose_query
from agents.retriever.ranker import rank_results, select_top_evidence
from agents.state.retriever_state import RetrieverState


def build_retriever_graph():
    """Assembles and compiles the LangGraph StateGraph for the Retriever Agent."""
    graph = StateGraph(RetrieverState)

    graph.add_node("analyze_query", analyze_query)
    graph.add_node("decompose_query", decompose_query)
    graph.add_node("search_multiple_queries", search_multiple_queries)
    graph.add_node("merge_results", merge_results)
    graph.add_node("deduplicate_chunks", deduplicate_chunks)
    graph.add_node("rank_results", rank_results)
    graph.add_node("select_top_evidence", select_top_evidence)

    graph.add_edge(START, "analyze_query")
    graph.add_edge("analyze_query", "decompose_query")
    graph.add_edge("decompose_query", "search_multiple_queries")
    graph.add_edge("search_multiple_queries", "merge_results")
    graph.add_edge("merge_results", "deduplicate_chunks")
    graph.add_edge("deduplicate_chunks", "rank_results")
    graph.add_edge("rank_results", "select_top_evidence")
    graph.add_edge("select_top_evidence", END)

    return graph.compile()


# Compiled once at import time and reused — compiling a LangGraph graph has
# a small fixed cost, and the graph structure never changes at runtime.
_retriever_graph = build_retriever_graph()


def run_retriever_agent(query: str, k: int = 5) -> Dict[str, Any]:
    """
    Public entrypoint: runs the full Retriever Agent pipeline for one query.

    Returns the complete final state (not just `top_evidence`) so callers —
    the API layer, tests, or a future Critic Agent — can inspect
    intermediate stages (which sub-queries were used, how many duplicates
    were removed, etc.) for debugging and transparency, without needing to
    re-run the graph.
    """
    logger.info(f"Running Retriever Agent for query: {query!r} (k={k})")
    initial_state: RetrieverState = {"original_query": query, "k": k}
    final_state = _retriever_graph.invoke(initial_state)
    logger.info(
        f"Retriever Agent finished — {len(final_state.get('top_evidence', []))} "
        f"evidence chunk(s) returned."
    )
    return final_state
