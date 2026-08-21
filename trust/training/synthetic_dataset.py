"""
Dataset Preparation — Synthetic Bootstrap Dataset.

THE HONEST PROBLEM: training a supervised model needs labeled examples —
(features, correct_trust_score) pairs. We don't have thousands of those
yet. The `trust_score_logs` table (database/postgres/models/trust_score_log.py)
logs every trust computation we've ever run, but it only records what the
HAND-BUILT FORMULA decided, not whether that decision was actually
correct. Training on the formula's own output would just teach XGBoost to
imitate the formula — not to improve on it. That would be circular, and
we'd be shipping a model that adds complexity without adding value.

THE STANDARD SOLUTION (and what we do here): bootstrap a synthetic
dataset from domain knowledge, structured so the "ground truth" trust
score is a plausible but NONLINEAR function of the five features — one
the LINEAR hand-built formula cannot fully capture (e.g. an evidence set
with high agreement AND high reliability but from only one source should
be trusted noticeably less than the linear formula gives it credit for
— a real interaction effect between agreement and source count). Random
label noise is added on top, since real-world "was this actually
trustworthy" labels are never perfectly clean either.

This is a legitimate, common technique for cold-starting a model before
enough real labeled data exists — but it IS synthetic, and this file says
so at every step rather than pretending otherwise. The moment you have a
CSV or database table of real (features, human_verified_correct) pairs,
replace `generate_synthetic_dataset()` with `load_real_dataset(path)` —
everything downstream (feature engineering, training, evaluation) is
unchanged, because both return the same DataFrame shape.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "agreement_score",
    "source_reliability",
    "similarity_score",
    "contradiction_score",
    "source_count_score",
]
LABEL_COLUMN = "true_trust_score"


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(-x))


def generate_synthetic_dataset(n_samples: int = 4000, seed: int = 42) -> pd.DataFrame:
    """
    Generates `n_samples` synthetic (features, true_trust_score) rows.

    Feature generation (realistic correlation structure, not pure
    independent noise):
      - `agreement_score` and `contradiction_score` are anti-correlated
        (evidence sets with more agreement tend to have fewer detected
        contradictions) — modeled by drawing contradiction from
        `1 - agreement` plus noise, then clipping to [0, 1].
      - `source_reliability` and `similarity_score` are drawn independently
        (a source can be authoritative but off-topic, or vice versa).
      - `source_count_score` is drawn independently (how many distinct
        documents happened to be retrieved is mostly orthogonal to how
        good any single one is).

    Label generation (the "ground truth" trust score each row is trained
    toward):
      A nonlinear combination of the features, run through a sigmoid to
      keep it in [0, 1], PLUS a penalty term when agreement is high but
      source_count is low (single-source over-confidence — a pattern a
      linear formula weights the same regardless of source count, but
      which arguably deserves extra caution), PLUS Gaussian label noise
      to simulate the fact that real "was this actually correct" labels
      are never perfectly clean.
    """
    rng = np.random.default_rng(seed)

    agreement_score = rng.beta(2.5, 2.0, n_samples)  # skews toward mid-high agreement
    contradiction_score = np.clip(1 - agreement_score + rng.normal(0, 0.15, n_samples), 0, 1)
    source_reliability = rng.beta(2.0, 2.0, n_samples)
    similarity_score = rng.beta(2.5, 1.8, n_samples)
    source_count_score = rng.beta(1.8, 1.5, n_samples)

    # Nonlinear "true" trust signal: weighted sum in logit-space, then a
    # single-source-overconfidence penalty subtracted before the sigmoid.
    logit = (
        3.2 * agreement_score
        + 2.0 * source_reliability
        + 1.6 * similarity_score
        - 2.4 * contradiction_score
        + 0.4 * source_count_score
        - 2.0  # centers the sigmoid around a realistic midpoint
    )
    single_source_penalty = np.where(
        (agreement_score > 0.7) & (source_count_score < 0.34), 0.9, 0.0
    )
    true_trust_score = _sigmoid(logit - single_source_penalty)

    # Label noise: real correctness labels are never perfectly clean.
    true_trust_score = np.clip(true_trust_score + rng.normal(0, 0.05, n_samples), 0, 1)

    df = pd.DataFrame(
        {
            "agreement_score": agreement_score,
            "source_reliability": source_reliability,
            "similarity_score": similarity_score,
            "contradiction_score": contradiction_score,
            "source_count_score": source_count_score,
            LABEL_COLUMN: true_trust_score,
        }
    )
    return df


def load_dataset(csv_path: Optional[str] = None, n_samples: int = 4000, seed: int = 42) -> pd.DataFrame:
    """
    Single entry point the training pipeline calls. Loads a real labeled
    CSV if one is provided (expected columns: the five FEATURE_COLUMNS
    plus LABEL_COLUMN), otherwise falls back to the synthetic generator.

    This mirrors the LLM/heuristic fallback pattern used everywhere else
    in this project (query decomposition, contradiction detection,
    synthesis): prefer the real thing, degrade gracefully to a documented
    substitute when it isn't available yet.
    """
    if csv_path:
        df = pd.read_csv(csv_path)
        missing = set(FEATURE_COLUMNS + [LABEL_COLUMN]) - set(df.columns)
        if missing:
            raise ValueError(f"Dataset at {csv_path} is missing required columns: {missing}")
        return df
    return generate_synthetic_dataset(n_samples=n_samples, seed=seed)
