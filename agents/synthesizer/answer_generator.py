"""
Synthesizer Node 2 — Generate Draft Answer.

Primary path: LLM, given only the verified evidence (and, on a retry, the
Verifier's revision feedback from the previous attempt).

Fallback: a purely extractive answer — literally the verified evidence's
own sentences, concatenated with citation markers, no rephrasing at all.
This fallback can't hallucinate almost by construction (it never generates
new wording, only quotes what's already there), which makes it a safe
degrade path, not just a cheap one — the tradeoff is fluency, not safety.
"""

from __future__ import annotations

from typing import Any, Dict, List

from loguru import logger
from pydantic import BaseModel, Field

from agents.llm_client import get_groq_llm
from agents.prompts.synthesizer_prompts import (
    REVISION_FEEDBACK_TEMPLATE,
    SYNTHESIS_SYSTEM_PROMPT,
    SYNTHESIS_USER_TEMPLATE,
)
from agents.state.synthesis_state import SynthesisVerificationState

ABSTAIN_MESSAGE_TEMPLATE = (
    "I don't have reliable enough evidence to answer this confidently. {reason}"
)


class SynthesizedAnswer(BaseModel):
    answer: str = Field(description="The answer text, with inline [chunk_id] citations on every factual sentence.")


def _llm_generate(query: str, evidence: List[Dict[str, Any]], revision_feedback: str | None) -> str:
    llm = get_groq_llm(temperature=0.2, timeout=20)

    evidence_block = "\n".join(f"{c['chunk_id']}: {c['text']}" for c in evidence)
    revision_block = (
        REVISION_FEEDBACK_TEMPLATE.format(feedback=revision_feedback) if revision_feedback else ""
    )

    structured_llm = llm.with_structured_output(SynthesizedAnswer)
    result = structured_llm.invoke(
        [
            ("system", SYNTHESIS_SYSTEM_PROMPT),
            (
                "human",
                SYNTHESIS_USER_TEMPLATE.format(
                    query=query, evidence_block=evidence_block, revision_block=revision_block
                ),
            ),
        ]
    )
    return result.answer


def _heuristic_generate(evidence: List[Dict[str, Any]]) -> str:
    """
    Purely extractive fallback: one sentence per verified chunk, each
    ending in its citation, exactly as the LLM path would format it — so
    the Verifier Agent can check both paths the same way.
    """
    lines = []
    for chunk in evidence:
        text = chunk["text"].strip()
        # Keep it short — first sentence of the chunk is usually the core claim.
        first_sentence = text.split(". ")[0].rstrip(".") + "."
        lines.append(f"{first_sentence} [{chunk['chunk_id']}]")
    return " ".join(lines)


def generate_draft_answer(state: SynthesisVerificationState) -> Dict[str, Any]:
    """LangGraph node: reads `verified_evidence`, `abstained`,
    `revision_feedback` (if this is a retry); writes `draft_answer`,
    `citations`, `synthesis_method`."""
    if state.get("abstained"):
        return {
            "draft_answer": ABSTAIN_MESSAGE_TEMPLATE.format(reason=state.get("abstain_reason", "")),
            "citations": [],
            "synthesis_method": "abstained",
        }

    evidence = state["verified_evidence"]
    revision_feedback = state.get("revision_feedback")

    try:
        draft_answer = _llm_generate(state["original_query"], evidence, revision_feedback)
        method = "llm"
    except Exception as exc:
        logger.warning(f"LLM synthesis unavailable ({exc}); falling back to extractive heuristic.")
        draft_answer = _heuristic_generate(evidence)
        method = "heuristic"

    citations = [
        {"chunk_id": c["chunk_id"], "source_title": c.get("source_title", ""), "doc_id": c.get("doc_id", "")}
        for c in evidence
    ]

    logger.info(f"Draft answer generated via {method} ({'retry' if revision_feedback else 'first attempt'}).")
    return {"draft_answer": draft_answer, "citations": citations, "synthesis_method": method}
