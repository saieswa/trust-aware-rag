"""
Node 4 — Detect Contradictions.

Primary path: ask an LLM (structured output) to find pairs of chunks that
factually disagree — see agents/prompts/critic_prompts.py for the full
reasoning behind that prompt's wording.

Fallback: if the LLM is unavailable (no API key, network issue, timeout),
fall back to a deterministic lexical heuristic:
  1. Compute topic overlap between every pair of chunks (shared significant
     keywords) — two chunks are only compared further if they're plausibly
     about the same specific topic.
  2. For topically-overlapping pairs, compute a "polarity" score from
     hand-picked positive/negative marker phrases (e.g. "entitled to" vs
     "do not qualify"). If one chunk reads positive and the other reads
     negative on the same topic, flag it as a contradiction.

This mirrors the same graceful-degradation pattern used in the Retriever
Agent's query decomposer: a missing LLM should degrade precision, not
break the pipeline.
"""

from __future__ import annotations

import itertools
import re
from typing import Any, Dict, List, Tuple

from loguru import logger
from pydantic import BaseModel, Field

from agents.llm_client import get_groq_llm
from agents.prompts.critic_prompts import (
    CONTRADICTION_DETECTION_SYSTEM_PROMPT,
    CONTRADICTION_DETECTION_USER_TEMPLATE,
)
from agents.state.critic_state import CriticState

# ---------- Heuristic fallback configuration ----------
_STOPWORDS = {
    "the", "a", "an", "is", "are", "of", "to", "for", "and", "or", "in", "on",
    "this", "that", "with", "as", "be", "by", "from", "at", "it", "under",
    "within", "will", "may", "not", "does", "do", "if", "than",
}
TOPIC_OVERLAP_THRESHOLD = 0.18  # Jaccard similarity on significant keywords

POSITIVE_MARKERS = (
    "entitled to", "supersedes all previous", "no issues at all",
    "no problems", "totally fine", "eligible for", "is safe",
)
NEGATIVE_MARKERS = (
    "do not qualify", "non-refundable", "historical reference only",
    "is not recommended", "avoid the combination", "should be transitioned",
)


class ContradictionPair(BaseModel):
    chunk_id_a: str
    chunk_id_b: str
    explanation: str = Field(description="What each side claims, in one sentence.")


class ContradictionList(BaseModel):
    contradictions: List[ContradictionPair]


def _llm_detect_contradictions(evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    llm = get_groq_llm(temperature=0, timeout=20)

    evidence_block = "\n".join(f"{c['chunk_id']}: {c['text']}" for c in evidence)

    structured_llm = llm.with_structured_output(ContradictionList)
    result = structured_llm.invoke(
        [
            ("system", CONTRADICTION_DETECTION_SYSTEM_PROMPT),
            ("human", CONTRADICTION_DETECTION_USER_TEMPLATE.format(evidence_block=evidence_block)),
        ]
    )
    return [c.model_dump() for c in result.contradictions]


def _tokenize(text: str) -> set:
    words = re.findall(r"[a-z]+", text.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


def _extract_entities(text: str) -> set:
    """
    Extract multi-word capitalized entities (e.g. "Drug X", "Drug Y").

    Plain bag-of-words Jaccard on lowercased single tokens loses exactly
    this kind of signal: "Drug X" and "Drug Y" both collapse to the single
    generic token "drug", which is far too weak on its own to prove two
    chunks share a specific topic. Named multi-word entities are a much
    stronger, more precise topic-match signal, so they're checked
    separately and treated as an overlap match even when the general
    Jaccard score is low.
    """
    matches = re.findall(r"\b[A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)+\b", text)
    return {m.lower() for m in matches}


def _topics_overlap(text_a: str, text_b: str, tokens_a: set, tokens_b: set) -> Tuple[bool, float]:
    """Returns (is_same_topic, jaccard_score). Same-topic if either the
    general keyword Jaccard clears the threshold, OR the two chunks share
    a named multi-word entity."""
    jaccard = _jaccard(tokens_a, tokens_b)
    shared_entities = _extract_entities(text_a) & _extract_entities(text_b)
    return (jaccard >= TOPIC_OVERLAP_THRESHOLD or bool(shared_entities)), jaccard


def _jaccard(set_a: set, set_b: set) -> float:
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union else 0.0


def _polarity(text: str) -> int:
    """Returns +1 if positive markers dominate, -1 if negative markers
    dominate, 0 if neither (or evenly matched)."""
    lowered = text.lower()
    positive_hits = sum(1 for marker in POSITIVE_MARKERS if marker in lowered)
    negative_hits = sum(1 for marker in NEGATIVE_MARKERS if marker in lowered)
    if positive_hits > negative_hits:
        return 1
    if negative_hits > positive_hits:
        return -1
    return 0


def _heuristic_detect_contradictions(evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    keyword_sets = {c["chunk_id"]: _tokenize(c["text"]) for c in evidence}
    polarities = {c["chunk_id"]: _polarity(c["text"]) for c in evidence}
    text_by_id = {c["chunk_id"]: c["text"] for c in evidence}

    contradictions: List[Dict[str, Any]] = []
    for chunk_a, chunk_b in itertools.combinations(evidence, 2):
        id_a, id_b = chunk_a["chunk_id"], chunk_b["chunk_id"]
        same_topic, overlap = _topics_overlap(
            text_by_id[id_a], text_by_id[id_b], keyword_sets[id_a], keyword_sets[id_b]
        )
        if not same_topic:
            continue  # not plausibly about the same specific topic

        pol_a, pol_b = polarities[id_a], polarities[id_b]
        if pol_a != 0 and pol_b != 0 and pol_a != pol_b:
            contradictions.append(
                {
                    "chunk_id_a": id_a,
                    "chunk_id_b": id_b,
                    "explanation": (
                        f"Chunks share topic (keyword overlap={overlap:.2f}) but read as "
                        f"opposite in stance based on their wording."
                    ),
                }
            )
    return contradictions


def detect_contradictions(state: CriticState) -> Dict[str, Any]:
    """LangGraph node: reads `normalized_evidence`, writes `contradictions`
    and `contradiction_method`."""
    evidence = state["normalized_evidence"]

    if len(evidence) < 2:
        return {"contradictions": [], "contradiction_method": "none"}

    try:
        contradictions = _llm_detect_contradictions(evidence)
        method = "llm"
    except Exception as exc:
        logger.warning(f"LLM contradiction detection unavailable ({exc}); falling back to heuristic.")
        contradictions = _heuristic_detect_contradictions(evidence)
        method = "heuristic"

    logger.info(f"Detected {len(contradictions)} contradiction pair(s) via {method}.")
    return {"contradictions": contradictions, "contradiction_method": method}
