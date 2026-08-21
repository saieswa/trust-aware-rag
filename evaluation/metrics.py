"""
Evaluation Metrics.

Every metric here uses a standard, named definition from the literature
— nothing invented for this project — so results are directly comparable
to how these datasets are normally scored.
"""

from __future__ import annotations

import re
import string
from collections import Counter
from typing import Dict, List, Tuple

import numpy as np
from sklearn.metrics import precision_recall_fscore_support


def _normalize_text(text: str) -> str:
    """Lowercase, strip punctuation, remove articles, collapse whitespace
    — the standard normalization used by SQuAD and HotpotQA's official
    evaluation scripts, so token overlap isn't penalized by superficial
    formatting differences."""
    text = text.lower()
    text = "".join(ch for ch in text if ch not in string.punctuation)
    text = re.sub(r"\b(a|an|the)\b", " ", text)
    return " ".join(text.split())


def token_f1(prediction: str, gold: str) -> Tuple[float, float, float]:
    """
    Token-level Precision / Recall / F1 — the standard HotpotQA/SQuAD
    answer-matching metric (not exact string match, since a correct
    answer is often embedded in a longer, fully-cited sentence).

    Precision = shared tokens / tokens in the PREDICTION
        — of everything the system said, how much was actually relevant?
    Recall    = shared tokens / tokens in the GOLD answer
        — of what the correct answer required, how much did the system say?
    F1        = harmonic mean of precision and recall.
    """
    pred_tokens = _normalize_text(prediction).split()
    gold_tokens = _normalize_text(gold).split()

    if not pred_tokens or not gold_tokens:
        return (0.0, 0.0, 0.0)

    common = Counter(pred_tokens) & Counter(gold_tokens)
    num_same = sum(common.values())

    if num_same == 0:
        return (0.0, 0.0, 0.0)

    precision = num_same / len(pred_tokens)
    recall = num_same / len(gold_tokens)
    f1 = 2 * precision * recall / (precision + recall)
    return (precision, recall, f1)


def answer_is_correct(prediction: str, gold: str, f1_threshold: float = 0.5) -> bool:
    """An answer counts as correct if its token-F1 against the gold
    answer clears `f1_threshold` — the standard looser-than-exact-match
    criterion used across QA benchmarks."""
    _, _, f1 = token_f1(prediction, gold)
    return f1 >= f1_threshold


def classification_metrics(y_true: List[str], y_pred: List[str], labels: List[str]) -> Dict:
    """
    Standard multi-class Precision / Recall / F1, macro-averaged (every
    class weighted equally regardless of frequency — appropriate here
    since FEVER's three labels are conceptually equally important, not
    proportional to their count in our small subset).

    Precision (per class) — "when the system said REFUTES, how often was
    it actually REFUTES?"
    Recall (per class) — "of all the actual REFUTES claims, how many did
    the system catch?"
    """
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, average=None, zero_division=0
    )
    macro_p, macro_r, macro_f1, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, average="macro", zero_division=0
    )

    per_class = {
        label: {
            "precision": round(float(p), 4),
            "recall": round(float(r), 4),
            "f1": round(float(f), 4),
            "support": int(s),
        }
        for label, p, r, f, s in zip(labels, precision, recall, f1, support)
    }

    return {
        "per_class": per_class,
        "macro_precision": round(float(macro_p), 4),
        "macro_recall": round(float(macro_r), 4),
        "macro_f1": round(float(macro_f1), 4),
        "accuracy": round(float(np.mean([t == p for t, p in zip(y_true, y_pred)])), 4),
    }


def expected_calibration_error(confidences: List[float], correctness: List[bool], n_bins: int = 10) -> Dict:
    """
    ECE (Expected Calibration Error): bins predictions by confidence
    (here, trust_score), and within each bin compares the AVERAGE
    predicted confidence to the ACTUAL fraction correct. A perfectly
    calibrated system has "trust_score ~0.8" predictions that are
    actually correct about 80% of the time. ECE is the weighted average
    gap between predicted and actual across all bins — 0 is perfect
    calibration.

        ECE = sum over bins of (bin_size / total) * |mean_confidence - accuracy|

    Also returns per-bin data for a reliability diagram (x = predicted
    confidence, y = actual accuracy, diagonal = perfect calibration).
    """
    confidences_arr = np.array(confidences)
    correctness_arr = np.array(correctness, dtype=float)
    bin_edges = np.linspace(0, 1, n_bins + 1)

    bins = []
    ece = 0.0
    n_total = len(confidences_arr)

    for i in range(n_bins):
        lo, hi = bin_edges[i], bin_edges[i + 1]
        if i == n_bins - 1:
            mask = (confidences_arr >= lo) & (confidences_arr <= hi)
        else:
            mask = (confidences_arr >= lo) & (confidences_arr < hi)

        bin_count = int(mask.sum())
        if bin_count == 0:
            bins.append(
                {"bin_range": [round(float(lo), 2), round(float(hi), 2)], "count": 0, "mean_confidence": None, "accuracy": None}
            )
            continue

        mean_confidence = float(confidences_arr[mask].mean())
        accuracy = float(correctness_arr[mask].mean())
        bins.append(
            {
                "bin_range": [round(float(lo), 2), round(float(hi), 2)],
                "count": bin_count,
                "mean_confidence": round(mean_confidence, 4),
                "accuracy": round(accuracy, 4),
            }
        )
        ece += (bin_count / n_total) * abs(mean_confidence - accuracy)

    brier_score = float(np.mean((confidences_arr - correctness_arr) ** 2))

    return {"ece": round(ece, 4), "brier_score": round(brier_score, 4), "bins": bins}


def hallucination_rate(hallucination_ratios: List[float]) -> float:
    """Mean fraction of unsupported sentences per answer, averaged across
    every evaluated question — read directly from the Verifier Agent's
    own per-answer hallucination_ratio."""
    if not hallucination_ratios:
        return 0.0
    return round(float(np.mean(hallucination_ratios)), 4)
