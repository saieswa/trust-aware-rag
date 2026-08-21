"""
Results Aggregation.

Takes the flat per-item records from run_benchmark.py and computes every
final metric the report needs: accuracy, hallucination rate,
precision/recall/F1 (dataset-appropriate definition — classification for
FEVER, span-matching for HotpotQA), and trust calibration — for both the
Trust-Aware system and the Baseline RAG, so every number has a direct
comparison point.
"""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np

from evaluation.metrics import classification_metrics, expected_calibration_error, hallucination_rate


def aggregate_fever(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    labels = ["SUPPORTS", "REFUTES", "NOT ENOUGH INFO"]
    gold = [r["gold_label"] for r in records]
    system_pred = [r["system_predicted_label"] for r in records]
    baseline_pred = [r["baseline_predicted_label"] for r in records]

    return {
        "n_items": len(records),
        "system": classification_metrics(gold, system_pred, labels),
        "baseline": classification_metrics(gold, baseline_pred, labels),
        "system_hallucination_rate": hallucination_rate([r["system_hallucination_ratio"] for r in records]),
        "baseline_hallucination_rate": hallucination_rate([r["baseline_hallucination_ratio"] for r in records]),
    }


def aggregate_hotpotqa(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    def _mean(key: str, prefix: str) -> float:
        return round(float(np.mean([r[f"{prefix}_{key}"] for r in records])), 4)

    return {
        "n_items": len(records),
        "system": {
            "accuracy": round(float(np.mean([r["system_correct"] for r in records])), 4),
            "precision": _mean("precision", "system"),
            "recall": _mean("recall", "system"),
            "f1": _mean("f1", "system"),
        },
        "baseline": {
            "accuracy": round(float(np.mean([r["baseline_correct"] for r in records])), 4),
            "precision": _mean("precision", "baseline"),
            "recall": _mean("recall", "baseline"),
            "f1": _mean("f1", "baseline"),
        },
        "system_hallucination_rate": hallucination_rate([r["system_hallucination_ratio"] for r in records]),
        "baseline_hallucination_rate": hallucination_rate([r["baseline_hallucination_ratio"] for r in records]),
    }


def aggregate_truthfulqa(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "n_items": len(records),
        "system": {"accuracy": round(float(np.mean([r["system_correct"] for r in records])), 4)},
        "baseline": {"accuracy": round(float(np.mean([r["baseline_correct"] for r in records])), 4)},
        "system_hallucination_rate": hallucination_rate([r["system_hallucination_ratio"] for r in records]),
        "baseline_hallucination_rate": hallucination_rate([r["baseline_hallucination_ratio"] for r in records]),
    }


def aggregate_trust_calibration(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calibration is only meaningful for the Trust-Aware system — the
    baseline has no confidence signal to calibrate at all, which is
    itself a reportable qualitative difference between the two systems."""
    confidences = [r["system_trust_score"] for r in records]
    correctness = [r["system_correct"] for r in records]
    return expected_calibration_error(confidences, correctness, n_bins=5)


def aggregate_all(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_dataset = {"fever": [], "hotpotqa": [], "truthfulqa": []}
    for r in records:
        by_dataset[r["dataset"]].append(r)

    return {
        "fever": aggregate_fever(by_dataset["fever"]) if by_dataset["fever"] else None,
        "hotpotqa": aggregate_hotpotqa(by_dataset["hotpotqa"]) if by_dataset["hotpotqa"] else None,
        "truthfulqa": aggregate_truthfulqa(by_dataset["truthfulqa"]) if by_dataset["truthfulqa"] else None,
        "trust_calibration": aggregate_trust_calibration(records),
        "overall": {
            "n_items": len(records),
            "system_accuracy": round(float(np.mean([r["system_correct"] for r in records])), 4),
            "baseline_accuracy": round(float(np.mean([r["baseline_correct"] for r in records])), 4),
            "system_hallucination_rate": hallucination_rate([r["system_hallucination_ratio"] for r in records]),
            "baseline_hallucination_rate": hallucination_rate([r["baseline_hallucination_ratio"] for r in records]),
            "system_abstention_rate": round(
                float(np.mean([r["system_status"] in ("abstained", "verification_failed") for r in records])), 4
            ),
        },
    }
