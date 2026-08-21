"""
Full Evaluation — Top-Level Entrypoint.

Runs the benchmark across all three datasets, aggregates metrics, saves
raw per-item results to CSV, saves aggregated metrics to JSON, and
generates every chart the research report references.

Usage:
    PYTHONPATH=backend:. python -m evaluation.run_full_evaluation
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from evaluation.aggregate_results import aggregate_all
from evaluation.generate_charts import generate_all_charts
from evaluation.run_benchmark import run_benchmark

REPORTS_DIR = Path(__file__).parent / "reports"


def main(embedder=None, truthfulqa_n: int = 40, max_retries: int = 1) -> dict:
    logger.info("Starting full evaluation run...")
    records = run_benchmark(embedder=embedder, truthfulqa_n=truthfulqa_n, max_retries=max_retries)
    logger.info(f"Benchmark complete — {len(records)} item(s) evaluated.")

    aggregated = aggregate_all(records)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # ---------- Raw per-item results (CSV) ----------
    csv_path = REPORTS_DIR / "raw_results.csv"
    if records:
        all_keys = sorted({k for r in records for k in r.keys()})
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=all_keys)
            writer.writeheader()
            writer.writerows(records)
    logger.info(f"Raw results saved to {csv_path}")

    # ---------- Aggregated metrics (JSON) ----------
    metadata = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "n_items": len(records),
        "truthfulqa_n": truthfulqa_n,
        "max_retries": max_retries,
    }
    metrics_path = REPORTS_DIR / "aggregated_metrics.json"
    metrics_path.write_text(json.dumps({"metadata": metadata, **aggregated}, indent=2))
    logger.info(f"Aggregated metrics saved to {metrics_path}")

    # ---------- Charts ----------
    chart_paths = generate_all_charts(aggregated, records, REPORTS_DIR / "charts")
    logger.info(f"Charts saved to {chart_paths}")

    return {"records": records, "aggregated": aggregated, "metadata": metadata, "chart_paths": chart_paths}


if __name__ == "__main__":
    main()
