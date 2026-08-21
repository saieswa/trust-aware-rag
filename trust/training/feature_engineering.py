"""
Feature Engineering.

IMPORTANT ML CONCEPT: tree-based models like XGBoost can, in principle,
discover feature interactions on their own — a single tree can split on
agreement_score, then split again on source_count_score within that
branch, effectively learning "IF agreement is high AND source_count is
low THEN ..." without ever being told to. This is a key advantage over
linear models (like our hand-built formula), which can only ever combine
features as a fixed weighted sum and can never express that kind of
conditional interaction.

So why engineer features at all here? Two practical reasons:
  1. Data efficiency — with a modest number of training rows, explicitly
     handing the model a pre-computed interaction term means it doesn't
     have to spend tree splits "rediscovering" a pattern that's already
     obvious from domain knowledge; it can spend its limited capacity
     elsewhere.
  2. Interpretability — an explicit `agreement_x_reliability` column shows
     up directly in the feature importance ranking with a clear name,
     which is easier to explain in a report than "the model implicitly
     learned this by combining splits on two other features."

Every engineered feature here is a genuine hypothesis about how these
signals interact, mirroring the reasoning already used in the hand-built
formula and the synthetic label's single-source penalty — not arbitrary
feature-generation-for-its-own-sake.
"""

from __future__ import annotations

import pandas as pd

from trust.training.synthetic_dataset import FEATURE_COLUMNS

ENGINEERED_FEATURE_COLUMNS = [
    "agreement_x_reliability",
    "net_agreement",
    "low_source_flag",
    "evidence_strength",
]

ALL_MODEL_FEATURES = FEATURE_COLUMNS + ENGINEERED_FEATURE_COLUMNS


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Adds engineered columns to a DataFrame that already has the five
    raw feature columns. Returns a new DataFrame — never mutates the
    input, so the same raw dataset can be re-engineered differently in
    an experiment without side effects."""
    df = df.copy()

    # Interaction term: evidence that BOTH agrees AND comes from reliable
    # sources is a stronger signal than either alone — multiplying
    # captures "both must be true," which a linear sum cannot express
    # (a sum treats a high value in either as equally good).
    df["agreement_x_reliability"] = df["agreement_score"] * df["source_reliability"]

    # Net agreement: agreement minus contradiction in one number — useful
    # because these two are already anti-correlated by construction, so a
    # single "net" signal is often cleaner for a shallow tree than
    # reasoning about two separately-thresholded features.
    df["net_agreement"] = df["agreement_score"] - df["contradiction_score"]

    # Binary flag for the exact pattern the synthetic label penalizes:
    # strong agreement from very few sources. Binary/threshold features
    # give a tree an exact, zero-cost split point instead of having to
    # approximate a threshold from a continuous variable.
    df["low_source_flag"] = ((df["agreement_score"] > 0.7) & (df["source_count_score"] < 0.34)).astype(float)

    # A simple composite "evidence strength" — the mean of the three
    # positive-direction signals — gives the model one pre-aggregated
    # summary feature alongside the raw ones.
    df["evidence_strength"] = df[["agreement_score", "source_reliability", "similarity_score"]].mean(axis=1)

    return df
