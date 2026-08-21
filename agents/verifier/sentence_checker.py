"""
Verifier Node 2 — Check Sentence Support (Detect Unsupported Claims).

Primary path: LLM, given every sentence and every evidence chunk, judges
each sentence supported/unsupported (see verifier_prompts.py for the full
reasoning behind that prompt).

Fallback: a word-overlap heuristic. Every sentence in our draft answer
ends with an explicit `[chunk_id]` citation (both the LLM and heuristic
synthesis paths are built to always include one) — so the fallback's job
is simply to verify that citation is HONEST: does the cited chunk's text
actually share enough vocabulary with the sentence to plausibly support
it? This catches the most basic and important failure mode (a sentence
citing a chunk that doesn't actually say that) even with zero LLM calls.
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
MIN_OVERLAP_FOR_SUPPORT = 0.25


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
    words = re.findall(r"[a-z]+", text.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


def _word_overlap(a: set, b: set) -> float:
    if not a:
        return 0.0
    return len(a & b) / len(a)


def _heuristic_check(sentences: List[str], evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    evidence_by_id = {c["chunk_id"]: c["text"] for c in evidence}
    evidence_tokens_by_id = {cid: _tokenize(text) for cid, text in evidence_by_id.items()}

    verdicts: List[Dict[str, Any]] = []
    for sentence in sentences:
        cited_ids = _CITATION_PATTERN.findall(sentence)
        clean_sentence = _CITATION_PATTERN.sub("", sentence).strip()
        sentence_tokens = _tokenize(clean_sentence)

        if not cited_ids:
            verdicts.append(
                {
                    "sentence": sentence,
                    "verdict": "unsupported",
                    "suggestion": "This sentence has no citation — add one or remove the claim.",
                }
            )
            continue

        best_overlap = max(
            (_word_overlap(sentence_tokens, evidence_tokens_by_id.get(cid, set())) for cid in cited_ids),
            default=0.0,
        )

        if best_overlap >= MIN_OVERLAP_FOR_SUPPORT:
            verdicts.append({"sentence": sentence, "verdict": "supported", "suggestion": None})
        else:
            verdicts.append(
                {
                    "sentence": sentence,
                    "verdict": "unsupported",
                    "suggestion": (
                        f"Cited chunk(s) {cited_ids} don't share enough wording with this "
                        f"sentence (overlap={best_overlap:.2f}) — rephrase to closely match "
                        f"what the cited chunk actually says, or remove the claim."
                    ),
                }
            )
    return verdicts


def check_sentence_support(state: SynthesisVerificationState) -> Dict[str, Any]:
    """LangGraph node: reads `sentences`, `verified_evidence`; writes
    `sentence_verdicts`, `hallucination_ratio`, `verification_method`."""
    if state.get("abstained"):
        return {"sentence_verdicts": [], "hallucination_ratio": 0.0, "verification_method": "none"}

    sentences = state["sentences"]
    evidence = state["verified_evidence"]

    if not sentences:
        return {"sentence_verdicts": [], "hallucination_ratio": 0.0, "verification_method": "none"}

    try:
        verdicts = _llm_check(sentences, evidence)
        if not verdicts:
            raise ValueError("LLM returned no verdicts.")
        method = "llm"
    except Exception as exc:
        logger.warning(f"LLM sentence verification unavailable ({exc}); falling back to heuristic.")
        verdicts = _heuristic_check(sentences, evidence)
        method = "heuristic"

    unsupported_count = sum(1 for v in verdicts if v["verdict"] == "unsupported")
    hallucination_ratio = round(unsupported_count / len(verdicts), 4)

    logger.info(
        f"Verifier: {unsupported_count}/{len(verdicts)} sentence(s) unsupported "
        f"(hallucination_ratio={hallucination_ratio}) via {method}."
    )
    return {"sentence_verdicts": verdicts, "hallucination_ratio": hallucination_ratio, "verification_method": method}
