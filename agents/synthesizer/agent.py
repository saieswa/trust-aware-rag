"""
Synthesizer Agent — Standalone Graph Assembly.

    ┌──────────────────────────┐
    │ select_verified_evidence  │  Node 1 — filter to "support"-labeled
    │                            │  chunks only; decide abstention
    └───────────┬───────────────┘
                ▼
    ┌────────────────────┐
    │ generate_draft_answer│  Node 2 — LLM (or grounded extractive fallback)
    └────────────────────┘

This standalone graph is used directly by the combined pipeline
(agents/pipeline/agent.py), which reuses these same two node functions
inside a larger graph that adds the Verifier and the retry loop. Exposed
here too so the Synthesizer can be run and tested in isolation.
"""

from __future__ import annotations

from typing import Any, Dict

from langgraph.graph import END, START, StateGraph
from loguru import logger

from agents.state.synthesis_state import SynthesisVerificationState
from agents.synthesizer.answer_generator import generate_draft_answer
from agents.synthesizer.evidence_selector import select_verified_evidence


def build_synthesizer_graph():
    graph = StateGraph(SynthesisVerificationState)
    graph.add_node("select_verified_evidence", select_verified_evidence)
    graph.add_node("generate_draft_answer", generate_draft_answer)
    graph.add_edge(START, "select_verified_evidence")
    graph.add_edge("select_verified_evidence", "generate_draft_answer")
    graph.add_edge("generate_draft_answer", END)
    return graph.compile()


_synthesizer_graph = build_synthesizer_graph()


def run_synthesizer_agent(query: str, trust_report: Dict[str, Any]) -> Dict[str, Any]:
    """Public entrypoint for running the Synthesizer Agent on its own
    (without the Verifier's checking/retry loop)."""
    logger.info(f"Running Synthesizer Agent for query: {query!r}")
    initial_state: SynthesisVerificationState = {"original_query": query, "trust_report": trust_report}
    return _synthesizer_graph.invoke(initial_state)
