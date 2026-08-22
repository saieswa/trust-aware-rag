"""
Retriever Agent — Graph Assembly with Document Scoping.

Wires the seven nodes into a LangGraph pipeline and accepts an optional `doc_id`
to guarantee all retrieval operations are strictly scoped to the active document.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from langgraph.graph import END, START, StateGraph
from loguru import logger

from agents.retriever.merge_and_dedup import deduplicate_chunks, merge_results
from agents.retriever.multi_search import search_multiple_queries
from agents.retriever.query_analyzer import analyze_query
from agents.retriever.query_decomposer import decompose_query
from agents.retriever.ranker import rank_results, select_top_evidence
from agents.state.retriever_state import RetrieverState


def build_retriever_graph():
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


_retriever_graph = build_retriever_graph()


def run_retriever_agent(query: str, k: int = 5, doc_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Runs the full Retriever Agent pipeline for one query, optionally restricted to doc_id.
    """
    logger.info(f"[RETRIEVAL] Running Retriever Agent for query: {query!r} (k={k}, doc_id={doc_id!r})")
    initial_state: RetrieverState = {
        "original_query": query,
        "k": k,
        "doc_id": doc_id,
    }
    final_state = _retriever_graph.invoke(initial_state)
    logger.info(
        f"[RETRIEVAL] Retriever Agent finished: {len(final_state.get('top_evidence', []))} "
        f"evidence chunk(s) returned for doc_id={doc_id!r}."
    )
    return final_state
