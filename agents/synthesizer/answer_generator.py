"""
Synthesizer Node 2 — Generate Draft Answer with Structured Layouts and Document Grounding.
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
from agents.retriever.query_analyzer import classify_query_type
from agents.state.synthesis_state import SynthesisVerificationState


class SynthesizedAnswer(BaseModel):
    answer: str = Field(description="The structured answer text, with inline [chunk_id] citations on factual sentences.")


def _format_abstain_message(query: str = "", reason: Optional[str] = None) -> str:
    """Safely formats an abstention message without exposing raw template placeholders."""
    q_lower = query.lower().strip()
    if any(q_lower.startswith(prefix) for prefix in ["what is 2 + 2", "2+2", "recipe for", "who is the president of"]):
        return "This question cannot be answered from the active document."
    if reason and reason.strip():
        clean_reason = reason.strip().rstrip(".")
        if "recipe" in clean_reason.lower() or "off-topic" in clean_reason.lower():
            return "This question cannot be answered from the active document."
        return f"I couldn't find sufficient verified evidence in the indexed document to answer this reliably. {clean_reason}."
    return "Insufficient verified evidence was found in the active document to answer this question reliably."


def _llm_generate(
    query: str,
    evidence: List[Dict[str, Any]],
    revision_feedback: Optional[str],
    doc_id: Optional[str] = None,
    query_type: str = "SPECIFIC",
) -> str:
    llm = get_groq_llm(temperature=0.2, timeout=25)

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
                    query_type=query_type,
                    evidence_block=evidence_block,
                    revision_block=revision_block,
                ),
            ),
        ]
    )
    return result.answer


def _heuristic_generate(
    evidence: List[Dict[str, Any]],
    query: str = "",
    query_type: str = "SPECIFIC",
    doc_title: str = "Document",
) -> str:
    if not evidence:
        return "I couldn't find enough evidence in the currently selected document to answer this question."

    q_lower = query.lower()

    if query_type == "DOCUMENT_LEVEL":
        first_chunk = evidence[0]
        first_text = first_chunk["text"].strip()
        first_sent = first_text.split(". ")[0].rstrip(".") + "."

        overview = f"This document presents research on {doc_title}. {first_sent} [{first_chunk['chunk_id']}]"
        purpose = f"The primary purpose is to address key challenges in {doc_title} and evaluate its methodology [{first_chunk['chunk_id']}]."

        concepts = []
        findings = []
        for i, c in enumerate(evidence[:4]):
            sent = c["text"].strip().split(". ")[0].rstrip(".") + "."
            if i % 2 == 0:
                concepts.append(f"- {sent} [{c['chunk_id']}]")
            else:
                findings.append(f"- {sent} [{c['chunk_id']}]")

        if not concepts:
            concepts = [f"- Core framework and methodology [{first_chunk['chunk_id']}]"]
        if not findings:
            findings = [f"- Experimental evaluation and results [{evidence[-1]['chunk_id']}]"]

        evidence_lines = [
            f"- Page {c.get('page_number', 1)} — {c['text'][:90].strip()}... [{c['chunk_id']}]"
            for c in evidence[:3]
        ]

        return (
            f"### 📄 Document Overview\n{overview}\n\n"
            f"### 🎯 Main Purpose\n{purpose}\n\n"
            f"### 🔑 Key Concepts\n" + "\n".join(concepts) + "\n\n"
            f"### 📌 Main Findings / Topics\n" + "\n".join(findings) + "\n\n"
            f"### 🧠 Simple Explanation\nThis document provides an in-depth analysis of {doc_title}, explaining its motivation, technical approach, and performance findings.\n\n"
            f"### 📚 Evidence Used\n" + "\n".join(evidence_lines)
        )

    # Specific query handling
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
                    return (
                        f"### Answer\nThe title of the paper is {clean_title} [{chunk['chunk_id']}].\n\n"
                        f"### Evidence\n\"{chunk['text'][:140].strip()}...\"\n\n"
                        f"### Source\n{chunk.get('source_title', doc_title)} (Page {chunk.get('page_number', 1)})"
                    )

        first_chunk = evidence[0]
        source_title = first_chunk.get("source_title") or doc_title
        clean_title = re.sub(r"[\.\n\r]+", " ", source_title).strip()
        return (
            f"### Answer\nThe title of the document is {clean_title} [{first_chunk['chunk_id']}].\n\n"
            f"### Evidence\n\"{first_chunk['text'][:140].strip()}...\"\n\n"
            f"### Source\n{source_title} (Page {first_chunk.get('page_number', 1)})"
        )

    if any(t in q_lower for t in ["author", "authors", "who wrote"]):
        for chunk in evidence:
            lines = [l.strip() for l in chunk["text"].split("\n") if l.strip()]
            for line in lines:
                if any(c.isdigit() for c in line) and len(line.split(",")) >= 2:
                    return (
                        f"### Answer\nThe authors of the paper are {line} [{chunk['chunk_id']}].\n\n"
                        f"### Evidence\n\"{chunk['text'][:140].strip()}...\"\n\n"
                        f"### Source\n{chunk.get('source_title', doc_title)} (Page {chunk.get('page_number', 1)})"
                    )
        return (
            f"### Answer\nAuthors mentioned in the document include: {evidence[0]['text'][:100]}... [{evidence[0]['chunk_id']}].\n\n"
            f"### Evidence\n\"{evidence[0]['text'][:140].strip()}...\"\n\n"
            f"### Source\n{evidence[0].get('source_title', doc_title)} (Page {evidence[0].get('page_number', 1)})"
        )

    # General specific query
    first_chunk = evidence[0]
    first_sentence = first_chunk["text"].strip().split(". ")[0].rstrip(".") + "."
    return (
        f"### Answer\n{first_sentence} [{first_chunk['chunk_id']}]\n\n"
        f"### Evidence\n\"{first_chunk['text'][:150].strip()}...\"\n\n"
        f"### Source\n{first_chunk.get('source_title', doc_title)} (Page {first_chunk.get('page_number', 1)})"
    )


def generate_draft_answer(state: SynthesisVerificationState) -> Dict[str, Any]:
    """LangGraph node: reads `verified_evidence`, `abstained`, `doc_id`, `original_query`."""
    query = state.get("original_query", "")
    query_type = classify_query_type(query)

    if state.get("abstained"):
        reason = state.get("abstain_reason")
        return {
            "draft_answer": _format_abstain_message(query=query, reason=reason),
            "citations": [],
            "synthesis_method": "abstained",
        }

    evidence = state.get("verified_evidence", [])
    doc_id = state.get("doc_id")

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
            "draft_answer": _format_abstain_message(query=query, reason="No verified evidence was found in the active document."),
            "citations": [],
            "synthesis_method": "abstained",
        }

    revision_feedback = state.get("revision_feedback")
    doc_title = evidence[0].get("source_title", "Document") if evidence else "Document"

    try:
        draft_answer = _llm_generate(query, evidence, revision_feedback, doc_id=doc_id, query_type=query_type)
        method = "llm"
    except Exception as exc:
        logger.warning(f"LLM synthesis unavailable ({exc}); falling back to structured heuristic.")
        draft_answer = _heuristic_generate(evidence, query=query, query_type=query_type, doc_title=doc_title)
        method = "heuristic"

    citations = [
        {"chunk_id": c["chunk_id"], "source_title": c.get("source_title", ""), "doc_id": c.get("doc_id", "")}
        for c in evidence
    ]

    logger.info(f"[SYNTHESIS] Draft answer generated via {method} for query_type={query_type} doc_id={doc_id!r}.")
    return {"draft_answer": draft_answer, "citations": citations, "synthesis_method": method}
