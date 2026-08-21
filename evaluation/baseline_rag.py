"""
Baseline RAG.

This is deliberately a "standard RAG" implementation matching the
project's original problem statement: retrieve top-k chunks, then answer
directly from whatever was retrieved — no Critic Agent judging evidence
quality, no contradiction detection, no trust threshold, no Verifier
checking claims, and no ability to abstain. It always produces an answer.

This is the system the whole Trust-Aware pipeline is built to be better
than — the evaluation's entire point is to measure that gap honestly, on
the same questions, the same retrieval index, the same underlying search.
Only what happens AFTER retrieval differs.
"""

from __future__ import annotations

from typing import Any, Dict

from retrieval.retriever import RetrievalPipeline


def run_baseline_rag(query: str, pipeline: RetrievalPipeline, k: int = 5) -> Dict[str, Any]:
    """
    Naive RAG: retrieve top-k chunks, concatenate them into an answer with
    no judgment about quality, agreement, or contradiction. If two
    retrieved chunks disagree, both get blended into the answer — this is
    intentional, since that exact blending failure is what the Critic
    Agent and trust score exist to prevent.
    """
    chunks = pipeline.search(query, k=k)

    if not chunks:
        return {
            "final_answer": "I don't have information about that.",
            "used_chunk_ids": [],
            "abstained": False,
        }

    # Naive synthesis: no filtering by label, no quality check — every
    # retrieved chunk's text is blended into the answer regardless of
    # whether it agrees with the others.
    answer_text = " ".join(chunk.text for chunk in chunks)

    return {
        "final_answer": answer_text,
        "used_chunk_ids": [c.chunk_id for c in chunks],
        "abstained": False,  # baseline RAG never abstains, by construction
    }
