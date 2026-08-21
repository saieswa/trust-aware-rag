"""
Verifier Agent — Standalone Graph Assembly.

    ┌────────────────┐
    │ split_sentences │   Node 1 — break the draft answer into sentences
    └───────┬────────┘
            ▼
    ┌──────────────────────┐
    │ check_sentence_support│  Node 2 — LLM (or word-overlap heuristic)
    │                        │  judges each sentence supported/unsupported
    └───────┬──────────────┘
            ▼
    ┌────────────────┐
    │ decide_verdict  │   Node 3 — approve, or reject with revision suggestions
    └────────────────┘

Standalone here for isolated testing; the combined pipeline
(agents/pipeline/agent.py) reuses these same three node functions inside
the larger graph that adds the retry loop back into the Synthesizer.
"""

from __future__ import annotations

from typing import Any, Dict, List

from langgraph.graph import END, START, StateGraph
from loguru import logger

from agents.state.synthesis_state import SynthesisVerificationState
from agents.verifier.sentence_checker import check_sentence_support
from agents.verifier.sentence_splitter import split_sentences
from agents.verifier.verdict_decider import decide_verdict


def build_verifier_graph():
    graph = StateGraph(SynthesisVerificationState)
    graph.add_node("split_sentences", split_sentences)
    graph.add_node("check_sentence_support", check_sentence_support)
    graph.add_node("decide_verdict", decide_verdict)
    graph.add_edge(START, "split_sentences")
    graph.add_edge("split_sentences", "check_sentence_support")
    graph.add_edge("check_sentence_support", "decide_verdict")
    graph.add_edge("decide_verdict", END)
    return graph.compile()


_verifier_graph = build_verifier_graph()


def run_verifier_agent(draft_answer: str, verified_evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Public entrypoint for running the Verifier Agent on its own, against
    any draft answer (not necessarily one this project's Synthesizer wrote)."""
    logger.info("Running Verifier Agent standalone.")
    initial_state: SynthesisVerificationState = {
        "draft_answer": draft_answer,
        "verified_evidence": verified_evidence,
        "abstained": False,
    }
    return _verifier_graph.invoke(initial_state)
