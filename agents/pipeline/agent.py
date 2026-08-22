"""
Synthesizer + Verifier — Combined Pipeline with Retry Loop.

This is the first graph in the project with actual branching: after the
Verifier's decide_verdict node, a router function inspects the state and
sends execution to one of three places.

    ┌──────────────────────────┐
    │ select_verified_evidence  │  Synthesizer Node 1
    └───────────┬───────────────┘
                ▼
    ┌────────────────────┐
    │ generate_draft_answer│◄─────────────────────┐  Synthesizer Node 2
    └───────────┬─────────┘                       │  (loops back here on retry)
                ▼                                 │
    ┌────────────────┐                            │
    │ split_sentences │  Verifier Node 1           │
    └───────┬────────┘                            │
            ▼                                      │
    ┌──────────────────────┐                       │
    │ check_sentence_support│  Verifier Node 2      │
    └───────┬──────────────┘                       │
            ▼                                      │
    ┌────────────────┐                             │
    │ decide_verdict  │  Verifier Node 3            │
    └───────┬────────┘                             │
            │                                      │
      ┌─────┴──────────────┬───────────────────────┘
      │ approved            │ rejected AND retries remain
      ▼                      (increment retry_count,
┌──────────────────┐          carry revision_suggestions
│ finalize_response │          forward as revision_feedback)
└──────────────────┘
      ▲
      │ rejected AND retries exhausted
      └──────────────────────────────

If the Synthesizer already abstained (Node 1 decided there's no usable
evidence, or the trust score said to), the graph short-circuits straight
to finalize_response — there's nothing for the Verifier to check in a
fixed "I don't have enough evidence" message.
"""

from __future__ import annotations

from typing import Any, Dict, Literal

from langgraph.graph import END, START, StateGraph
from loguru import logger

from agents.pipeline.response_finalizer import finalize_response
from agents.state.synthesis_state import SynthesisVerificationState
from agents.synthesizer.answer_generator import generate_draft_answer
from agents.synthesizer.evidence_selector import select_verified_evidence
from agents.verifier.sentence_checker import check_sentence_support
from agents.verifier.sentence_splitter import split_sentences
from agents.verifier.verdict_decider import decide_verdict

DEFAULT_MAX_RETRIES = 2


def _prepare_retry(state: SynthesisVerificationState) -> Dict[str, Any]:
    """
    Runs on the edge back into the Synthesizer after a rejection: bumps
    the retry counter and turns the Verifier's revision_suggestions into
    the `revision_feedback` string the Synthesizer's prompt reads on its
    next attempt (see agents/prompts/synthesizer_prompts.py's
    REVISION_FEEDBACK_TEMPLATE).
    """
    retry_count = state.get("retry_count", 0) + 1
    feedback = "\n".join(f"- {s}" for s in state.get("revision_suggestions", []))
    logger.info(f"Retrying synthesis (attempt {retry_count}) with revision feedback.")
    return {"retry_count": retry_count, "revision_feedback": feedback}


def _route_after_synthesis(state: SynthesisVerificationState) -> Literal["verify", "finalize"]:
    """If the Synthesizer abstained, skip straight to finalize — no point
    fact-checking a fixed abstention message."""
    return "finalize" if state.get("abstained") else "verify"


def _route_after_verdict(state: SynthesisVerificationState) -> Literal["retry", "finalize"]:
    verdict = state.get("verification_verdict", "approved")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", DEFAULT_MAX_RETRIES)

    if verdict == "rejected" and retry_count < max_retries:
        return "retry"
    return "finalize"


def build_pipeline_graph():
    graph = StateGraph(SynthesisVerificationState)

    graph.add_node("select_verified_evidence", select_verified_evidence)
    graph.add_node("generate_draft_answer", generate_draft_answer)
    graph.add_node("split_sentences", split_sentences)
    graph.add_node("check_sentence_support", check_sentence_support)
    graph.add_node("decide_verdict", decide_verdict)
    graph.add_node("prepare_retry", _prepare_retry)
    graph.add_node("finalize_response", finalize_response)

    graph.add_edge(START, "select_verified_evidence")
    graph.add_edge("select_verified_evidence", "generate_draft_answer")

    graph.add_conditional_edges(
        "generate_draft_answer",
        _route_after_synthesis,
        {"verify": "split_sentences", "finalize": "finalize_response"},
    )

    graph.add_edge("split_sentences", "check_sentence_support")
    graph.add_edge("check_sentence_support", "decide_verdict")

    graph.add_conditional_edges(
        "decide_verdict",
        _route_after_verdict,
        {"retry": "prepare_retry", "finalize": "finalize_response"},
    )

    # The loop: prepare_retry feeds back into the Synthesizer's drafting
    # node, carrying revision_feedback and the incremented retry_count.
    graph.add_edge("prepare_retry", "generate_draft_answer")

    graph.add_edge("finalize_response", END)

    return graph.compile()


_pipeline_graph = build_pipeline_graph()


def run_full_pipeline(
    query: str,
    trust_report: Dict[str, Any],
    max_retries: int = DEFAULT_MAX_RETRIES,
    doc_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Public entrypoint: runs Synthesizer -> Verifier, retrying synthesis up
    to `max_retries` times if the Verifier rejects the draft, and returns
    the full final state.
    """
    logger.info(
        f"[SYNTHESIS] Running Synthesizer+Verifier pipeline for query: {query!r} "
        f"(doc_id={doc_id!r}, max_retries={max_retries})"
    )
    initial_state: SynthesisVerificationState = {
        "original_query": query,
        "trust_report": trust_report,
        "max_retries": max_retries,
        "retry_count": 0,
        "revision_feedback": None,
        "doc_id": doc_id,
    }
    final_state = _pipeline_graph.invoke(initial_state)
    return final_state
