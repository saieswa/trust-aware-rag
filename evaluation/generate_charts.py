"""
Chart Generation.

Produces every graph the research report references, saved as PNG files.
Matplotlib only (no seaborn dependency) — kept consistent with this
project's general preference for minimal dependencies.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import matplotlib

matplotlib.use("Agg")  # no display backend needed — headless chart generation
import matplotlib.pyplot as plt
import numpy as np

COLOR_SYSTEM = "#2FBE79"   # matches the app's signal-green
COLOR_BASELINE = "#8B98A8"  # matches the app's ink-muted
COLOR_ACCENT = "#E8A33D"    # matches the app's accent-phosphor


def plot_accuracy_comparison(aggregated: Dict[str, Any], output_path: Path) -> None:
    datasets = [d for d in ["fever", "hotpotqa", "truthfulqa"] if aggregated.get(d)]
    system_acc = [aggregated[d]["system"]["accuracy"] for d in datasets]
    baseline_acc = [aggregated[d]["baseline"]["accuracy"] for d in datasets]

    x = np.arange(len(datasets))
    width = 0.35

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar(x - width / 2, system_acc, width, label="Trust-Aware System", color=COLOR_SYSTEM)
    ax.bar(x + width / 2, baseline_acc, width, label="Baseline RAG", color=COLOR_BASELINE)
    ax.set_ylabel("Accuracy")
    ax.set_title("Accuracy by Dataset: Trust-Aware System vs. Baseline RAG")
    ax.set_xticks(x)
    ax.set_xticklabels([d.upper() if d != "hotpotqa" else "HotpotQA" for d in datasets])
    ax.set_ylim(0, 1)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_hallucination_comparison(aggregated: Dict[str, Any], output_path: Path) -> None:
    datasets = [d for d in ["fever", "hotpotqa", "truthfulqa"] if aggregated.get(d)]
    system_hall = [aggregated[d]["system_hallucination_rate"] for d in datasets]
    baseline_hall = [aggregated[d]["baseline_hallucination_rate"] for d in datasets]

    x = np.arange(len(datasets))
    width = 0.35

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar(x - width / 2, system_hall, width, label="Trust-Aware System", color=COLOR_SYSTEM)
    ax.bar(x + width / 2, baseline_hall, width, label="Baseline RAG", color="#E5484D")
    ax.set_ylabel("Hallucination Rate (fraction of unsupported sentences)")
    ax.set_title("Hallucination Rate by Dataset: Trust-Aware System vs. Baseline RAG")
    ax.set_xticks(x)
    ax.set_xticklabels([d.upper() if d != "hotpotqa" else "HotpotQA" for d in datasets])
    ax.set_ylim(0, 1)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_calibration_curve(calibration: Dict[str, Any], output_path: Path) -> None:
    """The standard reliability diagram: x = mean predicted trust score
    per bin, y = actual accuracy per bin. Points on the diagonal are
    perfectly calibrated; above the diagonal means under-confident, below
    means over-confident."""
    bins = [b for b in calibration["bins"] if b["count"] > 0]
    x = [b["mean_confidence"] for b in bins]
    y = [b["accuracy"] for b in bins]
    sizes = [max(b["count"] * 40, 60) for b in bins]

    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    ax.plot([0, 1], [0, 1], linestyle="--", color=COLOR_BASELINE, label="Perfect calibration")
    ax.scatter(x, y, s=sizes, color=COLOR_ACCENT, edgecolor="white", zorder=3, label="Trust score bins")
    ax.plot(x, y, color=COLOR_ACCENT, alpha=0.5, zorder=2)
    ax.set_xlabel("Mean predicted trust score (bin)")
    ax.set_ylabel("Actual accuracy (bin)")
    ax.set_title(f"Trust Calibration Curve  (ECE = {calibration['ece']:.3f}, Brier = {calibration['brier_score']:.3f})")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.legend(loc="upper left")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_decision_distribution(records, output_path: Path) -> None:
    from collections import Counter

    counts = Counter(r["system_decision"] for r in records)
    labels = ["answer", "retrieve_more", "abstain"]
    values = [counts.get(label, 0) for label in labels]
    colors = [COLOR_SYSTEM, COLOR_ACCENT, "#E5484D"]

    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    ax.bar(labels, values, color=colors)
    ax.set_ylabel("Number of questions")
    ax.set_title("Trust Score Decisions Across All Evaluated Questions")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def generate_all_charts(aggregated: Dict[str, Any], records, output_dir: Path) -> Dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "accuracy_comparison": output_dir / "accuracy_comparison.png",
        "hallucination_comparison": output_dir / "hallucination_comparison.png",
        "calibration_curve": output_dir / "calibration_curve.png",
        "decision_distribution": output_dir / "decision_distribution.png",
    }
    plot_accuracy_comparison(aggregated, paths["accuracy_comparison"])
    plot_hallucination_comparison(aggregated, paths["hallucination_comparison"])
    plot_calibration_curve(aggregated["trust_calibration"], paths["calibration_curve"])
    plot_decision_distribution(records, paths["decision_distribution"])
    return {k: str(v) for k, v in paths.items()}
