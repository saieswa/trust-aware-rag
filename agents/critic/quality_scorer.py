"""
Node 2 — Measure Evidence Quality, and Node 3 — Score Source Reliability.

Both are pure, deterministic heuristics — no LLM call. This is a
deliberate design choice: "how specific/well-formed is this text" and
"does this source look authoritative" are the kind of signals a trust
model (added in a later project step) needs to be numeric, stable, and
cheap to compute for every single chunk on every request — not something
we want depending on an LLM call's availability or non-determinism.

Two independent sub-scores are combined into one `quality_score`:

  specificity_score     — does the text contain concrete, checkable details
                           (numbers, dates, defined terms) vs. vague language?
  source_reliability_score — does the source's own wording signal an
                           authoritative document (a "guideline," "policy,"
                           dated revision) vs. a casual/anecdotal one (a
                           forum post, personal opinion)?
"""

from __future__ import annotations

import re
from typing import Any, Dict

from loguru import logger

from agents.state.critic_state import CriticState

# ---------- Specificity signals ----------
NUMBER_PATTERN = re.compile(r"\b\d+\b")
YEAR_PATTERN = re.compile(r"\b(19|20)\d{2}\b")

# ---------- Source reliability signals ----------
# Phrases that suggest an authoritative, formally maintained source.
AUTHORITATIVE_MARKERS = (
    "guideline", "policy", "clinical", "revision", "effective",
    "official", "peer-reviewed", "standard of care", "current policy",
)
# Phrases that suggest a casual, anecdotal, or explicitly outdated source.
CASUAL_OR_OUTDATED_MARKERS = (
    "forum", "posted by", "i think", "i feel", "in my experience",
    "just sharing", "reply from", "archived", "historical reference only",
    "overblown",
)


def _specificity_score(text: str) -> float:
    """
    Higher when the text contains concrete, checkable details.

    Rationale: a claim like "refunds within 30 days" is falsifiable and
    specific; "refunds are usually processed pretty quickly" is vague and
    harder to verify or rely on. We count numbers and years as cheap,
    reliable proxies for specificity without needing any NLP model.
    """
    number_count = len(NUMBER_PATTERN.findall(text))
    has_year = bool(YEAR_PATTERN.search(text))
    word_count = max(len(text.split()), 1)

    # Normalize: numbers-per-100-words, capped, plus a flat bonus for a
    # dated reference (dates are a strong specificity + recency signal).
    density = min(number_count / (word_count / 100), 5.0) / 5.0  # 0..1
    year_bonus = 0.2 if has_year else 0.0
    return round(min(density * 0.8 + year_bonus, 1.0), 3)


def _source_reliability_score(text: str, source_title: str) -> float:
    """
    Higher when the source's own language signals it's an authoritative,
    formally maintained document rather than a casual/anecdotal one.

    This is intentionally a shallow lexical heuristic, not a claim about
    absolute truth — a forum post can happen to be correct, and a
    guideline can be outdated. It's one input signal among several the
    eventual Trust Model combines, not a verdict on its own.
    """
    lowered = f"{source_title} {text}".lower()

    authoritative_hits = sum(1 for marker in AUTHORITATIVE_MARKERS if marker in lowered)
    casual_hits = sum(1 for marker in CASUAL_OR_OUTDATED_MARKERS if marker in lowered)

    # Start neutral, move up for authoritative signals, down for casual ones.
    score = 0.5 + 0.15 * authoritative_hits - 0.2 * casual_hits
    return round(max(0.0, min(score, 1.0)), 3)


def measure_evidence_quality_and_reliability(state: CriticState) -> Dict[str, Any]:
    """
    LangGraph node: reads `normalized_evidence`, writes `quality_scores`
    (keyed by chunk_id).

    `quality_score` combines both sub-scores with equal weight — specificity
    and source reliability are different failure modes (a vague official
    document and a specific-but-anecdotal post are both weaker evidence
    than a specific, authoritative one), so both need to pull the combined
    score down independently.
    """
    scores: Dict[str, Dict[str, Any]] = {}

    for chunk in state["normalized_evidence"]:
        specificity = _specificity_score(chunk["text"])
        reliability = _source_reliability_score(chunk["text"], chunk.get("source_title", ""))
        quality_score = round((specificity + reliability) / 2, 3)

        scores[chunk["chunk_id"]] = {
            "specificity_score": specificity,
            "source_reliability_score": reliability,
            "quality_score": quality_score,
        }

    logger.info(f"Scored quality/reliability for {len(scores)} chunk(s).")
    return {"quality_scores": scores}
