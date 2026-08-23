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


class StructuredDocOutput(BaseModel):
    document_overview: str = Field(description="1-2 clear sentences summarizing what the document is about.")
    main_idea: str = Field(description="The central problem, thesis, or objective of the document.")
    steps: List[str] = Field(description="3-4 step-by-step points explaining how the approach, workflow, or document develops.")
    key_points: List[str] = Field(description="3-4 key concepts, methods, or takeaways.")
    main_findings: List[str] = Field(description="3-4 major findings, results, or conclusions.")
    simple_explanation: str = Field(description="Simple, easy-to-understand explanation for a non-technical reader.")


class StructuredSpecificOutput(BaseModel):
    direct_answer: str = Field(description="Direct, concise answer to the specific question.")
    evidence_quote: str = Field(description="Short direct excerpt supporting the answer.")
    source_info: str = Field(description="Document name, page, and section.")


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


def _clean_internal_citations(text: str) -> str:
    """Removes raw internal chunk IDs like [doc_xxx_chunk0] from user-facing markdown."""
    return re.sub(r"\s*\[doc_[a-zA-Z0-9_]+\]", "", text).strip()


def _llm_generate(
    query: str,
    evidence: List[Dict[str, Any]],
    revision_feedback: Optional[str],
    doc_id: Optional[str] = None,
    query_type: str = "SPECIFIC",
    doc_title: str = "Document",
) -> tuple[str, Dict[str, Any]]:
    llm = get_groq_llm(temperature=0.2, timeout=25)

    evidence_block = "\n\n".join(
        f"[{c['chunk_id']}] (Page {c.get('page_number', '?')} | {c.get('section', 'General')}):\n{c['text']}"
        for c in evidence
    )
    revision_block = (
        REVISION_FEEDBACK_TEMPLATE.format(feedback=revision_feedback) if revision_feedback else ""
    )

    evidence_items = [
        {
            "page": c.get("page_number", 1) or 1,
            "text": (c["text"][:180].strip() + "…") if len(c["text"]) > 180 else c["text"].strip(),
            "source": c.get("source_title", doc_title),
            "chunk_id": c["chunk_id"],
        }
        for c in evidence[:3]
    ]

    if query_type == "DOCUMENT_LEVEL":
        structured_llm = llm.with_structured_output(StructuredDocOutput)
        res: StructuredDocOutput = structured_llm.invoke(
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

        steps_md = "\n".join(f"{i+1}. {s}" for i, s in enumerate(res.steps))
        key_points_md = "\n".join(f"• {k}" for k in res.key_points)
        findings_md = "\n".join(f"• {f}" for f in res.main_findings)

        markdown_answer = (
            f"### Document Overview\n{res.document_overview}\n\n"
            f"### Main Idea\n{res.main_idea}\n\n"
            f"### Step-by-Step Explanation\n{steps_md}\n\n"
            f"### Key Points\n{key_points_md}\n\n"
            f"### Main Findings & Topics\n{findings_md}\n\n"
            f"### Simple Explanation\n{res.simple_explanation}"
        )

        struct_dict = {
            "answer_type": "document_explanation",
            "document_overview": res.document_overview,
            "main_idea": res.main_idea,
            "steps": res.steps,
            "key_points": res.key_points,
            "main_findings": res.main_findings,
            "simple_explanation": res.simple_explanation,
            "evidence": evidence_items,
        }
        return markdown_answer, struct_dict

    else:
        structured_llm = llm.with_structured_output(StructuredSpecificOutput)
        spec_res: StructuredSpecificOutput = structured_llm.invoke(
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

        markdown_answer = (
            f"### Answer\n{spec_res.direct_answer}\n\n"
            f"### Evidence\n\"{spec_res.evidence_quote}\"\n\n"
            f"### Source\n{spec_res.source_info}"
        )

        struct_dict = {
            "answer_type": "specific_answer",
            "direct_answer": spec_res.direct_answer,
            "evidence_summary": spec_res.evidence_quote,
            "source_summary": spec_res.source_info,
            "evidence": evidence_items,
        }
        return markdown_answer, struct_dict


def _heuristic_generate(
    evidence: List[Dict[str, Any]],
    query: str = "",
    query_type: str = "SPECIFIC",
    doc_title: str = "Document",
) -> tuple[str, Dict[str, Any]]:
    if not evidence:
        msg = "I couldn't find enough evidence in the currently selected document to answer this question."
        return msg, {"answer_type": "abstention", "direct_answer": msg, "evidence": []}

    q_lower = query.lower()
    evidence_items = [
        {
            "page": c.get("page_number", 1) or 1,
            "text": (c["text"][:180].strip() + "…") if len(c["text"]) > 180 else c["text"].strip(),
            "source": c.get("source_title", doc_title),
            "chunk_id": c["chunk_id"],
        }
        for c in evidence[:3]
    ]

    if query_type == "DOCUMENT_LEVEL":
        first_chunk = evidence[0]
        first_text = first_chunk["text"].strip()
        first_sent = first_text.split(". ")[0].rstrip(".") + "."

        overview = f"This document presents research on {doc_title}. {first_sent}"
        main_idea = f"The primary goal is to address key challenges in {doc_title}: {first_sent}"

        steps = []
        for i, c in enumerate(evidence[:3]):
            s = c["text"].strip().split(". ")[0].rstrip(".") + "."
            steps.append(f"Section {i+1}: {s}")

        if not steps:
            steps = [f"Introduces the core concepts and findings of {doc_title}."]

        key_points = []
        main_findings = []
        for i, c in enumerate(evidence[:4]):
            sent = c["text"].strip().split(". ")[0].rstrip(".") + "."
            if i % 2 == 0:
                key_points.append(sent)
            else:
                main_findings.append(sent)

        if not key_points:
            key_points = [f"Foundational concepts for {doc_title}."]
        if not main_findings:
            main_findings = [f"Experimental and analytical results for {doc_title}."]

        simple_exp = f"In simple terms, this document explains {doc_title}, highlighting its methodology and results."

        steps_md = "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps))
        kp_md = "\n".join(f"• {k}" for k in key_points)
        mf_md = "\n".join(f"• {f}" for f in main_findings)

        markdown_answer = (
            f"### Document Overview\n{overview}\n\n"
            f"### Main Idea\n{main_idea}\n\n"
            f"### Step-by-Step Explanation\n{steps_md}\n\n"
            f"### Key Points\n{kp_md}\n\n"
            f"### Main Findings & Topics\n{mf_md}\n\n"
            f"### Simple Explanation\n{simple_exp}"
        )

        struct_dict = {
            "answer_type": "document_explanation",
            "document_overview": overview,
            "main_idea": main_idea,
            "steps": steps,
            "key_points": key_points,
            "main_findings": main_findings,
            "simple_explanation": simple_exp,
            "evidence": evidence_items,
        }
        return markdown_answer, struct_dict

    # Specific query handling
    if any(t in q_lower for t in ["title", "name of this"]):
        GENERIC_SECTIONS = {"abstract", "introduction", "guideline", "table", "figure", "section"}
        clean_title = doc_title
        for chunk in evidence:
            text = chunk["text"].strip()
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            for line in lines:
                if line.lower() in GENERIC_SECTIONS or line.lower().startswith("table") or line.lower().startswith("figure"):
                    continue
                if len(line) > 5:
                    clean_title = re.sub(r"[\.\n\r]+", " ", line).strip()
                    break

        direct_ans = f"The title of the paper is {clean_title}."
        quote = evidence[0]["text"][:140].strip() + "…"
        source = f"{doc_title} — Page {evidence[0].get('page_number', 1)}"

        markdown_answer = f"### Answer\n{direct_ans}\n\n### Evidence\n\"{quote}\"\n\n### Source\n{source}"
        struct_dict = {
            "answer_type": "specific_answer",
            "direct_answer": direct_ans,
            "evidence_summary": quote,
            "source_summary": source,
            "evidence": evidence_items,
        }
        return markdown_answer, struct_dict

    if any(t in q_lower for t in ["author", "authors", "who wrote"]):
        author_line = "Authors listed in document"
        for chunk in evidence:
            lines = [l.strip() for l in chunk["text"].split("\n") if l.strip()]
            for line in lines:
                if any(c.isdigit() for c in line) and len(line.split(",")) >= 2:
                    author_line = line
                    break

        direct_ans = f"The authors of the document are {author_line}."
        quote = evidence[0]["text"][:140].strip() + "…"
        source = f"{doc_title} — Page {evidence[0].get('page_number', 1)}"

        markdown_answer = f"### Answer\n{direct_ans}\n\n### Evidence\n\"{quote}\"\n\n### Source\n{source}"
        struct_dict = {
            "answer_type": "specific_answer",
            "direct_answer": direct_ans,
            "evidence_summary": quote,
            "source_summary": source,
            "evidence": evidence_items,
        }
        return markdown_answer, struct_dict

    # General specific question
    first_chunk = evidence[0]
    direct_ans = first_chunk["text"].strip().split(". ")[0].rstrip(".") + "."
    quote = first_chunk["text"][:140].strip() + "…"
    source = f"{doc_title} — Page {first_chunk.get('page_number', 1)}"

    markdown_answer = f"### Answer\n{direct_ans}\n\n### Evidence\n\"{quote}\"\n\n### Source\n{source}"
    struct_dict = {
        "answer_type": "specific_answer",
        "direct_answer": direct_ans,
        "evidence_summary": quote,
        "source_summary": source,
        "evidence": evidence_items,
    }
    return markdown_answer, struct_dict


def generate_draft_answer(state: SynthesisVerificationState) -> Dict[str, Any]:
    """LangGraph node: reads `verified_evidence`, `abstained`, `doc_id`, `original_query`."""
    query = state.get("original_query", "")
    query_type = classify_query_type(query)

    if state.get("abstained"):
        reason = state.get("abstain_reason")
        msg = _format_abstain_message(query=query, reason=reason)
        return {
            "draft_answer": msg,
            "structured_answer": {
                "answer_type": "abstention",
                "direct_answer": msg,
                "evidence": [],
            },
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
        msg = _format_abstain_message(query=query, reason="No verified evidence was found in the active document.")
        return {
            "draft_answer": msg,
            "structured_answer": {
                "answer_type": "abstention",
                "direct_answer": msg,
                "evidence": [],
            },
            "citations": [],
            "synthesis_method": "abstained",
        }

    revision_feedback = state.get("revision_feedback")
    doc_title = evidence[0].get("source_title", "Document") if evidence else "Document"

    try:
        draft_answer, struct_dict = _llm_generate(
            query, evidence, revision_feedback, doc_id=doc_id, query_type=query_type, doc_title=doc_title
        )
        method = "llm"
    except Exception as exc:
        logger.warning(f"LLM synthesis unavailable ({exc}); falling back to structured heuristic.")
        draft_answer, struct_dict = _heuristic_generate(
            evidence, query=query, query_type=query_type, doc_title=doc_title
        )
        method = "heuristic"

    citations = [
        {"chunk_id": c["chunk_id"], "source_title": c.get("source_title", ""), "doc_id": c.get("doc_id", "")}
        for c in evidence
    ]

    logger.info(f"[SYNTHESIS] Draft answer generated via {method} for query_type={query_type} doc_id={doc_id!r}.")
    return {
        "draft_answer": draft_answer,
        "structured_answer": struct_dict,
        "citations": citations,
        "synthesis_method": method,
    }
