"""
Training Pipeline.

ML CONCEPTS EXPLAINED IN THIS FILE:

Gradient Boosting (what XGBoost actually is):
    XGBoost builds an ensemble of small decision trees, one at a time.
    The first tree makes a rough prediction. The second tree is trained
    not on the original labels, but on the RESIDUAL ERROR of the first
    tree (how wrong it was, and in which direction). The third tree
    corrects the combined error of the first two, and so on. Each tree is
    deliberately weak (shallow, few splits) — the power comes from
    hundreds of weak trees each nudging the prediction a little closer to
    correct, not from any single tree being smart on its own.

Train / Validation / Test split (why three sets, not two):
    - TRAIN: what the model actually learns from (fits tree splits to).
    - VALIDATION: used *during* training to decide when to stop adding
      more trees (see "early stopping" below) — the model never learns
      from this data directly, but our TRAINING PROCESS uses it to make
      decisions, so it's not a fully unbiased final judge either.
    - TEST: touched exactly once, after training is completely finished,
      to report final metrics. This is the only number that honestly
      answers "how will this model perform on data it's never
      influenced in any way."

Overfitting & Early Stopping:
    A model with too many trees, too deep, will eventually start
    memorizing noise in the training set instead of learning the general
    pattern — training error keeps dropping, but validation error starts
    rising. Early stopping watches validation error after every new tree
    and stops adding trees once it hasn't improved for
    `early_stopping_rounds` consecutive rounds, keeping the model at
    (approximately) its best generalization point instead of its lowest
    training error.

Regularization (max_depth, subsample, colsample_bytree):
    Additional guards against overfitting: `max_depth` limits how
    complex any single tree can get; `subsample`/`colsample_bytree` train
    each tree on a random subset of rows/columns (like a mini
    random-forest trick inside gradient boosting), which prevents any one
    tree from fitting too precisely to a specific quirk in the full
    dataset.

Learning Rate (eta):
    How much each new tree's correction is allowed to shift the overall
    prediction. A lower learning rate means each tree contributes a
    smaller nudge, requiring more trees to converge — slower to train,
    but generally generalizes better than a few large, aggressive
    corrections.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd
import xgboost as xgb
from loguru import logger
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from app.core.config import get_settings
from trust.formula.trust_formula import compute_trust_score
from trust.training.feature_engineering import ALL_MODEL_FEATURES, engineer_features
from trust.training.synthetic_dataset import LABEL_COLUMN, load_dataset

DEFAULT_XGB_PARAMS: Dict[str, Any] = {
    "n_estimators": 300,
    "max_depth": 4,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "objective": "reg:squarederror",
    "eval_metric": "rmse",
    "random_state": 42,
}


def _split_dataset(df: pd.DataFrame):
    """60/20/20 train/validation/test split. Validation is used during
    training for early stopping; test is held out completely and only
    touched once, at final evaluation."""
    train_df, temp_df = train_test_split(df, test_size=0.4, random_state=42)
    val_df, test_df = train_test_split(temp_df, test_size=0.5, random_state=42)
    return train_df, val_df, test_df


def _to_xy(df: pd.DataFrame):
    X = df[ALL_MODEL_FEATURES]
    y = df[LABEL_COLUMN]
    return X, y


def train_trust_model(
    csv_path: str | None = None,
    n_samples: int = 4000,
    xgb_params: Dict[str, Any] | None = None,
    early_stopping_rounds: int = 20,
) -> Dict[str, Any]:
    """
    Full training pipeline: load data -> engineer features -> split ->
    train with early stopping -> evaluate on the held-out test set ->
    compare against the hand-built formula baseline -> save the model and
    a metadata JSON file alongside it.
    """
    params = {**DEFAULT_XGB_PARAMS, **(xgb_params or {})}
    settings = get_settings()

    logger.info("Loading dataset...")
    raw_df = load_dataset(csv_path=csv_path, n_samples=n_samples)
    df = engineer_features(raw_df)

    train_df, val_df, test_df = _split_dataset(df)
    X_train, y_train = _to_xy(train_df)
    X_val, y_val = _to_xy(val_df)
    X_test, y_test = _to_xy(test_df)

    logger.info(
        f"Dataset split — train={len(train_df)} val={len(val_df)} test={len(test_df)} "
        f"(features: {ALL_MODEL_FEATURES})"
    )

    model = xgb.XGBRegressor(**params, early_stopping_rounds=early_stopping_rounds)

    logger.info("Training XGBoost regressor with early stopping on validation RMSE...")
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_train, y_train), (X_val, y_val)],
        verbose=False,
    )
    best_iteration = model.best_iteration
    logger.info(f"Training stopped at iteration {best_iteration} (of {params['n_estimators']} max).")

    metrics = _evaluate(model, X_test, y_test)
    baseline_metrics = _evaluate_formula_baseline(test_df, y_test)
    feature_importances = _feature_importances(model)

    model_path = Path(settings.TRUST_MODEL_PATH)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(str(model_path))

    metadata = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_samples": len(df),
        "train_size": len(train_df),
        "val_size": len(val_df),
        "test_size": len(test_df),
        "best_iteration": int(best_iteration) if best_iteration is not None else params["n_estimators"],
        "features": ALL_MODEL_FEATURES,
        "xgb_params": params,
        "test_metrics": metrics,
        "formula_baseline_metrics": baseline_metrics,
        "feature_importances": feature_importances,
        "model_path": str(model_path),
        "data_source": "synthetic" if not csv_path else csv_path,
    }

    metadata_path = model_path.with_name(model_path.stem + "_metadata.json")
    metadata_path.write_text(json.dumps(metadata, indent=2))
    logger.info(f"Model saved to {model_path}; metadata saved to {metadata_path}")

    return metadata


def _evaluate(model: xgb.XGBRegressor, X_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, float]:
    """
    RMSE (Root Mean Squared Error) — average prediction error, in the
    same units as the trust score itself (0-1), with larger errors
    penalized disproportionately. Lower is better; 0 is perfect.

    MAE (Mean Absolute Error) — average absolute prediction error,
    without the extra penalty on large errors — directly readable as "on
    average, the prediction is off by this much."

    R² (Coefficient of Determination) — fraction of variance in the true
    trust scores the model's predictions explain, from 0 (no better than
    always predicting the mean) to 1 (perfect). Scale-independent, so
    it's easier to judge "is this actually good" without extra context.
    """
    predictions = model.predict(X_test)
    rmse = float(np.sqrt(mean_squared_error(y_test, predictions)))
    mae = float(mean_absolute_error(y_test, predictions))
    r2 = float(r2_score(y_test, predictions))
    return {"rmse": round(rmse, 4), "mae": round(mae, 4), "r2": round(r2, 4)}


def _evaluate_formula_baseline(test_df: pd.DataFrame, y_test: pd.Series) -> Dict[str, float]:
    """Runs the EXISTING hand-built linear formula on the same test set,
    so the training report always shows, side by side, whether the
    trained model is actually better than what we already had."""
    formula_predictions = []
    for _, row in test_df.iterrows():
        features = {
            "agreement_score": row["agreement_score"],
            "source_reliability": row["source_reliability"],
            "similarity_score": row["similarity_score"],
            "contradiction_score": row["contradiction_score"],
            "source_count_score": row["source_count_score"],
        }
        formula_predictions.append(compute_trust_score(features)["trust_score"])

    formula_predictions = np.array(formula_predictions)
    rmse = float(np.sqrt(mean_squared_error(y_test, formula_predictions)))
    mae = float(mean_absolute_error(y_test, formula_predictions))
    r2 = float(r2_score(y_test, formula_predictions))
    return {"rmse": round(rmse, 4), "mae": round(mae, 4), "r2": round(r2, 4)}


def _feature_importances(model: xgb.XGBRegressor) -> Dict[str, float]:
    """
    Feature importance (gain-based): for every split any tree in the
    ensemble ever made on a given feature, how much did that split reduce
    prediction error, summed and normalized across all features. A high
    value means the model relied heavily on that feature — this is what
    makes a tree ensemble more interpretable than it might seem: even
    with hundreds of trees, we can still say concretely "here's what the
    model actually pays attention to."
    """
    importances = model.feature_importances_
    return {
        feature: round(float(score), 4)
        for feature, score in sorted(zip(ALL_MODEL_FEATURES, importances), key=lambda x: -x[1])
    }


if __name__ == "__main__":
    result = train_trust_model()
    print(json.dumps(result, indent=2))
