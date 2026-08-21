"""
Trust ML Model — Inference Wrapper.

Loads the XGBoost model saved by train_trust_model.py and exposes a
predict() function with the same shape as the hand-built formula's
compute_trust_score() (trust/formula/trust_formula.py) — a score plus a
per-feature breakdown — so trust/trust_engine.py can switch between them
without the rest of the pipeline (or the API layer) needing to know which
one actually ran.

ML CONCEPT — SHAP values / pred_contribs (feature attribution for a
black-box model):
    A linear formula's "feature contribution" is trivial: value × weight.
    A tree ensemble has no such simple per-feature weight — a feature's
    effect depends on which trees split on it, at what thresholds, and in
    combination with which other features along the way. XGBoost can
    still answer "how much did each feature push THIS SPECIFIC prediction
    up or down" via `pred_contribs=True`, which computes exact SHAP
    (SHapley Additive exPlanations) values: for one prediction, the sum of
    every feature's contribution plus a baseline ("expected value" over
    the whole training set) exactly equals the model's output. This is
    what makes a tree ensemble's prediction auditable per-request, not
    just in aggregate — a specific low trust score can point to "this
    prediction was pulled down by contradiction_score contributing -0.18"
    the same way the formula already does, just computed differently.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import xgboost as xgb
from loguru import logger

from app.core.config import get_settings
from trust.training.feature_engineering import ALL_MODEL_FEATURES, engineer_features
import pandas as pd


class TrustMLModel:
    """Wraps a trained XGBoost Booster for inference. `load()` returns
    None (not an exception) if no trained model exists yet — callers are
    expected to fall back to the formula, exactly like every other
    LLM-vs-heuristic fallback already in this project."""

    def __init__(self, booster: xgb.Booster, metadata: Dict[str, Any]):
        self.booster = booster
        self.metadata = metadata

    @classmethod
    def load(cls) -> Optional["TrustMLModel"]:
        settings = get_settings()
        model_path = Path(settings.TRUST_MODEL_PATH)
        metadata_path = model_path.with_name(model_path.stem + "_metadata.json")

        if not model_path.exists():
            logger.info(f"No trained trust model found at {model_path}.")
            return None

        booster = xgb.Booster()
        booster.load_model(str(model_path))

        metadata = {}
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text())

        logger.info(f"Loaded trust ML model from {model_path} (trained_at={metadata.get('trained_at', 'unknown')}).")
        return cls(booster, metadata)

    def predict(self, features: Dict[str, float]) -> Dict[str, Any]:
        """
        Mirrors compute_trust_score()'s return shape: {trust_score,
        decision, feature_breakdown}. `feature_breakdown` here holds each
        feature's SHAP contribution to THIS prediction rather than a
        formula weight × value — genuinely comparable in spirit (both
        answer "how much did this feature push the score"), computed
        differently under the hood.
        """
        raw_df = pd.DataFrame([features])
        engineered_df = engineer_features(raw_df)[ALL_MODEL_FEATURES]

        dmatrix = xgb.DMatrix(engineered_df)
        raw_score = float(self.booster.predict(dmatrix)[0])
        trust_score = round(min(max(raw_score, 0.0), 1.0), 4)

        contributions = self.booster.predict(dmatrix, pred_contribs=True)[0]
        # The last value returned by pred_contribs is the model's baseline
        # (the average prediction over the training set) — every other
        # value is that specific feature's push away from that baseline.
        base_value = float(contributions[-1])
        feature_contributions = {
            feature: round(float(value), 4)
            for feature, value in zip(ALL_MODEL_FEATURES, contributions[:-1])
        }

        decision = self._decide(trust_score)

        return {
            "trust_score": trust_score,
            "decision": decision,
            "method": "ml",
            "base_value": round(base_value, 4),
            "feature_contributions": feature_contributions,
            "model_trained_at": self.metadata.get("trained_at"),
        }

    def _decide(self, trust_score: float) -> str:
        settings = get_settings()
        if trust_score >= settings.TRUST_THRESHOLD_HIGH:
            return "answer"
        if trust_score >= settings.TRUST_THRESHOLD_LOW:
            return "retrieve_more"
        return "abstain"


_model_singleton: Optional[TrustMLModel] = None
_load_attempted = False


def get_trust_ml_model() -> Optional[TrustMLModel]:
    """
    Module-level singleton, loaded lazily on first request rather than at
    import time — importing this module (e.g. transitively, via
    trust_engine.py) should never fail just because no model has been
    trained yet. `_load_attempted` prevents re-reading from disk on every
    single call once we know there's no model there.
    """
    global _model_singleton, _load_attempted
    if _model_singleton is None and not _load_attempted:
        _model_singleton = TrustMLModel.load()
        _load_attempted = True
    return _model_singleton


def reset_trust_ml_model_cache() -> None:
    """Called after training a new model, so the next inference request
    picks up the freshly-trained model instead of a stale cached one (or
    a cached None from before training happened)."""
    global _model_singleton, _load_attempted
    _model_singleton = None
    _load_attempted = False
