"""
Formula-based Trust Score.

    trust_score = w1*agreement_score
                + w2*source_reliability
                + w3*similarity_score
                + w4*(1 - contradiction_score)
                + w5*source_count_score

Each w is a fixed weight (see WEIGHTS below), and every feature is already
normalized to [0, 1] by trust/features/feature_extraction.py. Because the
weights sum to 1.0 and every feature is in [0, 1], `trust_score` itself is
guaranteed to land in [0, 1] — no separate clamping needed.

WHY THIS SHAPE:
- agreement_score, source_reliability, similarity_score, and
  source_count_score all being HIGH should push trust UP — they're
  weighted with a plain positive coefficient.
- contradiction_score being HIGH should push trust DOWN — so it's
  subtracted from 1 first (`1 - contradiction_score`), turning "lots of
  contradiction" into "little credit," before being weighted the same way
  as the other four. This keeps every term in the sum meaning the same
  thing: "more of this term = more trust."

WHY THESE WEIGHTS:
- Agreement (0.35) is weighted highest — whether the evidence we'd
  actually use agrees with itself is the single strongest signal that an
  answer built from it will be correct.
- Source reliability (0.25) and similarity (0.20) both matter but are
  secondary to agreement — reliable, on-topic evidence that doesn't
  cohere is still risky to answer from.
- Contradiction (0.15) is a penalty term, not a primary driver — it's
  already partially reflected in a lower agreement_score, so it's
  weighted to reinforce, not double-count, that signal.
- Source count (0.05) is a minor tie-breaker — corroboration from
  independent documents is a good sign, but on its own it's the weakest
  of the five signals (many independent low-quality sources shouldn't
  outweigh one strong one).

This formula is intentionally simple and fully interpretable — every
number in the final score can be traced back to a specific, explainable
cause. Per the project roadmap, this hand-built formula is the baseline;
a trained model (e.g. XGBoost) is a drop-in replacement for
`compute_trust_score` once enough labeled real-world examples exist to
train one, without changing anything else in the pipeline.
"""

from __future__ import annotations

from typing import Any, Dict

from app.core.config import get_settings

WEIGHTS = {
    "agreement_score": 0.35,
    "source_reliability": 0.25,
    "similarity_score": 0.20,
    "contradiction_score": 0.15,  # applied as (1 - contradiction_score)
    "source_count_score": 0.05,
}

assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, "Trust score weights must sum to 1.0"


def compute_trust_score(features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Applies the weighted formula above to extracted features and returns a
    fully broken-down result: the final score, a decision, and each
    feature's individual contribution (value * weight) — so a low trust
    score is never a mystery number, it's traceable to exactly which
    feature(s) pulled it down.
    """
    agreement = features["agreement_score"]
    reliability = features["source_reliability"]
    similarity = features["similarity_score"]
    contradiction = features["contradiction_score"]
    source_count = features["source_count_score"]

    contribution_agreement = WEIGHTS["agreement_score"] * agreement
    contribution_reliability = WEIGHTS["source_reliability"] * reliability
    contribution_similarity = WEIGHTS["similarity_score"] * similarity
    contribution_contradiction = WEIGHTS["contradiction_score"] * (1 - contradiction)
    contribution_source_count = WEIGHTS["source_count_score"] * source_count

    trust_score = round(
        contribution_agreement
        + contribution_reliability
        + contribution_similarity
        + contribution_contradiction
        + contribution_source_count,
        4,
    )

    decision = _decide(trust_score)

    return {
        "trust_score": trust_score,
        "decision": decision,
        "feature_breakdown": {
            "agreement_score": {
                "value": agreement,
                "weight": WEIGHTS["agreement_score"],
                "contribution": round(contribution_agreement, 4),
            },
            "source_reliability": {
                "value": reliability,
                "weight": WEIGHTS["source_reliability"],
                "contribution": round(contribution_reliability, 4),
            },
            "similarity_score": {
                "value": similarity,
                "weight": WEIGHTS["similarity_score"],
                "contribution": round(contribution_similarity, 4),
            },
            "contradiction_score": {
                "value": contradiction,
                "weight": WEIGHTS["contradiction_score"],
                "applied_as": "1 - contradiction_score",
                "contribution": round(contribution_contradiction, 4),
            },
            "source_count_score": {
                "value": source_count,
                "weight": WEIGHTS["source_count_score"],
                "contribution": round(contribution_source_count, 4),
            },
        },
    }


def _decide(trust_score: float) -> str:
    """
    Decision policy:

        trust_score >= TRUST_THRESHOLD_HIGH  -> "answer"
        TRUST_THRESHOLD_LOW <= trust_score
                            < TRUST_THRESHOLD_HIGH -> "retrieve_more"
        trust_score < TRUST_THRESHOLD_LOW    -> "abstain"

    Thresholds are read from app settings (.env: TRUST_THRESHOLD_HIGH=0.75,
    TRUST_THRESHOLD_LOW=0.5 by default) rather than hard-coded, so they can
    be tuned per-deployment without a code change.
    """
    settings = get_settings()
    if trust_score >= settings.TRUST_THRESHOLD_HIGH:
        return "answer"
    if trust_score >= settings.TRUST_THRESHOLD_LOW:
        return "retrieve_more"
    return "abstain"
