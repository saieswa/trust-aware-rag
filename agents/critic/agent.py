"""
Critic Agent — Graph Assembly.

    ┌────────────────┐
    │ read_evidence   │   Node 1 — normalize/validate incoming evidence
    └───────┬────────┘
            ▼
    ┌────────────────────────────┐
    │ measure_evidence_quality_   │  Nodes 2+3 — specificity + source
    │ and_reliability             │  reliability heuristics -> quality_score
    └───────┬────────────────────┘
            ▼
    ┌────────────────────┐
    │ detect_contradictions│  Node 4 — LLM (or heuristic) pairwise fact-check
    └───────┬────────────┘
            ▼
    ┌────────────────┐
    │ label_evidence  │   Node 5 — support / contradict / neutral per chunk
    └───────┬────────┘
            ▼
    ┌────────────────────┐
    │ build_critic_report │  Final — assemble the structured JSON report
    └────────────────────┘

Linear pipeline, same style as the Retriever Agent — no branching yet.
Branching (e.g. "if contradiction_ratio is too high, request a second
retrieval pass") is a natural extension once this feeds the Synthesizer/
Verifier agents and the trust score in later steps.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from langgraph.graph import END, START, StateGraph
from loguru import logger

from agents.critic.contradiction_detector import detect_contradictions
from agents.critic.evidence_labeler import label_evidence
from agents.critic.evidence_reader import read_evidence
from agents.critic.quality_scorer import measure_evidence_quality_and_reliability
from agents.critic.report_builder import build_critic_report
from agents.state.critic_state import CriticState


def build_critic_graph():
    graph = StateGraph(CriticState)

    graph.add_node("read_evidence", read_evidence)
    graph.add_node("measure_evidence_quality_and_reliability", measure_evidence_quality_and_reliability)
    graph.add_node("detect_contradictions", detect_contradictions)
    graph.add_node("label_evidence", label_evidence)
    graph.add_node("build_critic_report", build_critic_report)

    graph.add_edge(START, "read_evidence")
    graph.add_edge("read_evidence", "measure_evidence_quality_and_reliability")
    graph.add_edge("measure_evidence_quality_and_reliability", "detect_contradictions")
    graph.add_edge("detect_contradictions", "label_evidence")
    graph.add_edge("label_evidence", "build_critic_report")
    graph.add_edge("build_critic_report", END)

    return graph.compile()


_critic_graph = build_critic_graph()


def run_critic_agent(query: str, evidence: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Public entrypoint: runs the full Critic Agent pipeline.

    `evidence` is expected to be the `top_evidence` list produced by the
    Retriever Agent (agents/retriever/agent.py) — a list of dicts with at
    least `chunk_id`, `doc_id`, `text`, `source_title`. Returns the full
    final state so callers can inspect intermediate stages if needed, but
    `critic_report` is the field everything downstream should actually use.
    """
    logger.info(f"Running Critic Agent for query: {query!r} over {len(evidence or [])} evidence chunk(s)")
    initial_state: CriticState = {"original_query": query, "evidence": evidence or []}
    final_state = _critic_graph.invoke(initial_state)
    return final_state
