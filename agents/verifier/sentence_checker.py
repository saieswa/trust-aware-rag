"""
Verifier Node 2 — Check Sentence Support (Detect Unsupported Claims).

Primary path: LLM, given every sentence and every evidence chunk, judges
each sentence supported/unsupported.
Fallback: Heuristic validating citation honesty and active document ownership.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Literal, Optional

from loguru import logger
from pydantic import BaseModel, Field

from agents.llm_client import get_groq_llm
from agents.prompts.verifier_prompts import (
    SENTENCE_SUPPORT_SYSTEM_PROMPT,
    SENTENCE_SUPPORT_USER_TEMPLATE,
)
from agents.state.synthesis_state import SynthesisVerificationState

_STOPWORDS = {
    "the", "a", "an", "is", "are", "of", "to", "for", "and", "or", "in", "on",
    "this", "that", "with", "as", "be", "by", "from", "at", "it", "its",
}
_CITATION_PATTERN = re.compile(r"\[([a-zA-Z0-9_]+)\]")
MIN_OVERLAP_FOR_SUPPORT = 0.10


class SentenceVerdict(BaseModel):
    sentence: str
    verdict: Literal["supported", "unsupported"]
    suggestion: Optional[str] = Field(default=None, description="Only for 'unsupported' sentences.")


class SentenceVerdictList(BaseModel):
    verdicts: List[SentenceVerdict]


def _llm_check(sentences: List[str], evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    llm = get_groq_llm(temperature=0, timeout=20)

    evidence_block = "\n".join(f"{c['chunk_id']}: {c['text']}" for c in evidence)
    sentence_block = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(sentences))

    structured_llm = llm.with_structured_output(SentenceVerdictList)
    result = structured_llm.invoke(
        [
            ("system", SENTENCE_SUPPORT_SYSTEM_PROMPT),
            ("human", SENTENCE_SUPPORT_USER_TEMPLATE.format(evidence_block=evidence_block, sentence_block=sentence_block)),
        ]
    )
    return [v.model_dump() for v in result.verdicts]


def _tokenize(text: str) -> set:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


def _word_overlap(a: set, b: set) -> float:
    if not a:
        return 1.0
    return len(a & b) / len(a)


def _heuristic_check(
    sentences: List[str],
    evidence: List[Dict[str, Any]],
    target_doc_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    evidence_by_id = {c["chunk_id"]: c["text"] for c in evidence}
    evidence_doc_by_id = {c["chunk_id"]: c.get("doc_id") for c in evidence}
    evidence_tokens_by_id = {cid: _tokenize(text) for cid, text in evidence_by_id.items()}

    verdicts: List[Dict[str, Any]] = []
    for sentence in sentences:
        cited_ids = _CITATION_PATTERN.findall(sentence)
        clean_sentence = _CITATION_PATTERN.sub("", sentence).strip()
        sentence_tokens = _tokenize(clean_sentence)

        # 1. Enforce strict document ownership
        if target_doc_id and cited_ids:
            wrong_doc_ids = [
                cid for cid in cited_ids
                if evidence_doc_by_id.get(cid) and evidence_doc_by_id.get(cid) != target_doc_id
            ]
            if wrong_doc_ids:
                verdicts.append(
                    {
                        "sentence": sentence,
                        "verdict": "unsupported",
                        "suggestion": f"Sentence cites chunks {wrong_doc_ids} from a different document instead of {target_doc_id}.",
                    }
                )
                continue

        # 2. If it cites valid chunks from the active document:
        valid_cited = [cid for cid in cited_ids if cid in evidence_by_id]
        if valid_cited:
            verdicts.append({"sentence": sentence, "verdict": "supported", "suggestion": None})
            continue

        # 3. If no citation or unindexed citation, check word overlap with evidence
        best_overlap = max(
            (_word_overlap(sentence_tokens, tokens) for tokens in evidence_tokens_by_id.values()),
            default=0.0,
        )

        if best_overlap >= MIN_OVERLAP_FOR_SUPPORT or not sentence_tokens:
            verdicts.append({"sentence": sentence, "verdict": "supported", "suggestion": None})
        else:
            verdicts.append(
                {
                    "sentence": sentence,
                    "verdict": "unsupported",
                    "suggestion": (
                        f"Sentence has no verified citation matching active document chunks "
                        f"(overlap={best_overlap:.2f}) — add a valid [chunk_id] citation."
                    ),
                }
            )
    return verdicts


def check_sentence_support(state: SynthesisVerificationState) -> Dict[str, Any]:
    """LangGraph node: reads `sentences`, `verified_evidence`, `doc_id`."""
    if state.get("abstained"):
        return {"sentence_verdicts": [], "hallucination_ratio": 0.0, "verification_method": "none"}

    sentences = state.get("sentences", [])
    evidence = state.get("verified_evidence", [])
    target_doc_id = state.get("doc_id")

    if not sentences:
        return {"sentence_verdicts": [], "hallucination_ratio": 0.0, "verification_method": "none"}

    try:
        verdicts = _llm_check(sentences, evidence)
        if not verdicts:
            raise ValueError("LLM returned no verdicts.")
        method = "llm"
    except Exception as exc:
        logger.warning(f"LLM sentence verification unavailable ({exc}); falling back to heuristic.")
        verdicts = _heuristic_check(sentences, evidence, target_doc_id=target_doc_id)
        method = "heuristic"

    unsupported_count = sum(1 for v in verdicts if v["verdict"] == "unsupported")
    hallucination_ratio = round(unsupported_count / len(verdicts), 4)

    logger.info(
        f"[VERIFICATION] doc_id={target_doc_id!r} {unsupported_count}/{len(verdicts)} sentence(s) unsupported "
        f"(hallucination_ratio={hallucination_ratio}) via {method}."
    )
    return {"sentence_verdicts": verdicts, "hallucination_ratio": hallucination_ratio, "verification_method": method}
