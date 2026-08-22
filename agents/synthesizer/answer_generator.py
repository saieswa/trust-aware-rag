"""
Synthesizer Node 2 — Generate Draft Answer with Document Grounding.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

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
    "I couldn't find sufficient verified evidence in the indexed document to answer this reliably. {reason}"
)


class SynthesizedAnswer(BaseModel):
    answer: str = Field(description="The answer text, with inline [chunk_id] citations on every factual sentence.")


def _llm_generate(
    query: str,
    evidence: List[Dict[str, Any]],
    revision_feedback: Optional[str],
    doc_id: Optional[str] = None,
) -> str:
    llm = get_groq_llm(temperature=0.2, timeout=20)

    evidence_block = "\n\n".join(
        f"[{c['chunk_id']}] (Page {c.get('page_number', '?')} | {c.get('section', 'General')}):\n{c['text']}"
        for c in evidence
    )
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
                    query=query,
                    doc_id=doc_id or "Current Document",
                    evidence_block=evidence_block,
                    revision_block=revision_block,
                ),
            ),
        ]
    )
    return result.answer


def _heuristic_generate(evidence: List[Dict[str, Any]], query: str = "") -> str:
    if not evidence:
        return "I couldn't find enough evidence in the currently selected document to answer this question."

    q_lower = query.lower()

    # Title query
    if any(t in q_lower for t in ["title", "name of this"]):
        GENERIC_SECTIONS = {"abstract", "introduction", "guideline", "table", "figure", "section"}
        for chunk in evidence:
            text = chunk["text"].strip()
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            for line in lines:
                if line.lower() in GENERIC_SECTIONS or line.lower().startswith("table") or line.lower().startswith("figure"):
                    continue
                if len(line) > 5:
                    clean_title = re.sub(r"[\.\n\r]+", " ", line).strip()
                    return f"The title of the paper is {clean_title} [{chunk['chunk_id']}]."

        first_chunk = evidence[0]
        source_title = first_chunk.get("source_title")
        if source_title and source_title not in ("Unknown Source", "Document"):
            clean_title = re.sub(r"[\.\n\r]+", " ", source_title).strip()
            return f"The title of the document is {clean_title} [{first_chunk['chunk_id']}]."

        first_sent = first_chunk["text"].strip().split(". ")[0]
        clean_title = re.sub(r"[\.\n\r]+", " ", first_sent).strip()
        return f"The title of the document is {clean_title} [{first_chunk['chunk_id']}]."

    # Author query
    if any(t in q_lower for t in ["author", "authors", "who wrote"]):
        for chunk in evidence:
            lines = [l.strip() for l in chunk["text"].split("\n") if l.strip()]
            for line in lines:
                if any(c.isdigit() for c in line) and len(line.split(",")) >= 2:
                    return f"The authors of the paper are {line}. [{chunk['chunk_id']}]"
        return f"Authors mentioned in the document include: {evidence[0]['text'][:120]}... [{evidence[0]['chunk_id']}]"

    # General query - extract concise first sentence from top 2 chunks
    lines = []
    for chunk in evidence[:2]:
        text = chunk["text"].strip()
        first_sentence = text.split(". ")[0].rstrip(".") + "."
        lines.append(f"{first_sentence} [{chunk['chunk_id']}]")
    return " ".join(lines)


def generate_draft_answer(state: SynthesisVerificationState) -> Dict[str, Any]:
    """LangGraph node: reads `verified_evidence`, `abstained`, `doc_id`."""
    if state.get("abstained"):
        return {
            "draft_answer": ABSTAIN_MESSAGE_TEMPLATE,
            "citations": [],
            "synthesis_method": "abstained",
        }

    evidence = state.get("verified_evidence", [])
    doc_id = state.get("doc_id")
    query = state.get("original_query", "")

    # Enforce strict document ownership
    if doc_id:
        valid_evidence = [c for c in evidence if c.get("doc_id") == doc_id]
        if len(valid_evidence) < len(evidence):
            logger.error(
                f"DOCUMENT ISOLATION ERROR: Discarded {len(evidence) - len(valid_evidence)} "
                f"chunks not belonging to active doc_id={doc_id!r} before answer synthesis."
            )
        evidence = valid_evidence

    if not evidence:
        return {
            "draft_answer": "I couldn't find enough evidence in the currently selected document to answer this question.",
            "citations": [],
            "synthesis_method": "abstained",
        }

    revision_feedback = state.get("revision_feedback")

    try:
        draft_answer = _llm_generate(query, evidence, revision_feedback, doc_id=doc_id)
        method = "llm"
    except Exception as exc:
        logger.warning(f"LLM synthesis unavailable ({exc}); falling back to extractive heuristic.")
        draft_answer = _heuristic_generate(evidence, query=query)
        method = "heuristic"

    citations = [
        {"chunk_id": c["chunk_id"], "source_title": c.get("source_title", ""), "doc_id": c.get("doc_id", "")}
        for c in evidence
    ]

    logger.info(f"[SYNTHESIS] Draft answer generated via {method} for doc_id={doc_id!r}.")
    return {"draft_answer": draft_answer, "citations": citations, "synthesis_method": method}
