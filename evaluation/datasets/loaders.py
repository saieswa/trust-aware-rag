"""
Evaluation Dataset Loaders.

DATA PROVENANCE — read this before trusting any number downstream:

  TruthfulQA: the REAL, FULL dataset (790 rows), downloaded directly from
  the official repo (github.com/sylinrl/TruthfulQA/TruthfulQA.csv). No
  curation, no fabrication — this is the actual benchmark.

  FEVER / HotpotQA: their official hosts (fever.ai, hotpotqa.github.io,
  and the associated S3 buckets) were not reachable from this evaluation
  environment, and the HuggingFace dataset viewer for FEVER is disabled
  for bulk download (it requires a Python loading script HuggingFace no
  longer auto-executes). Rather than fabricate results against data we
  don't actually have, evaluation/datasets/fever_subset.json and
  hotpotqa_subset.json are small, hand-curated sets (20 and 12 items)
  built in each dataset's exact real schema, using verifiable real-world
  facts. One FEVER row (fever_001) is the actual first training example
  from the real dataset, confirmed via the dataset's official card.

  This is a real methodological limitation of running this evaluation in
  a network-restricted environment, stated plainly rather than hidden.
  The loaders below are written so that swapping in the real, full
  FEVER/HotpotQA files (once downloaded in an environment with access)
  requires no code changes — only replacing the JSON files with the same
  schema at full scale.

TruthfulQA does not ship with retrieval context (it tests a model's own
generation, not RAG) — to evaluate it through OUR retrieval-based system,
each question is given a small synthetic two-document corpus: one
document stating the correct answer, one stating a common incorrect
answer as an unattributed "popular belief" source. This deliberately
recreates the exact scenario the project's Critic Agent exists to handle
— a retrieval corpus containing both a correct reference and a plausible
but false claim — and is documented here as a deliberate adaptation, not
a hidden one.
"""

from __future__ import annotations

import csv
import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

DATASETS_DIR = Path(__file__).parent


@dataclass
class EvalItem:
    id: str
    dataset: str  # "truthfulqa" | "fever" | "hotpotqa"
    question: str
    context_documents: List[Dict[str, str]]  # [{title, text}]
    gold: Dict[str, Any] = field(default_factory=dict)


def load_truthfulqa(n_samples: int = 40, seed: int = 42) -> List[EvalItem]:
    """Loads the real TruthfulQA.csv and builds a synthetic two-document
    corpus per question (see module docstring)."""
    path = DATASETS_DIR / "raw" / "truthfulqa_full.csv"
    rows = []
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    rng = random.Random(seed)
    sampled = rng.sample(rows, min(n_samples, len(rows)))

    items = []
    for i, row in enumerate(sampled):
        best_answer = row["Best Answer"].strip()
        incorrect = [a.strip() for a in row["Incorrect Answers"].split(";") if a.strip()]
        correct_all = [a.strip() for a in row["Correct Answers"].split(";") if a.strip()]
        best_incorrect = incorrect[0] if incorrect else row.get("Best Incorrect Answer", "").strip()

        context_documents = [
            {"title": "Reference Answer", "text": f"{row['Question']} {best_answer}"},
        ]
        if best_incorrect:
            context_documents.append(
                {
                    "title": "Common Belief (unverified forum post)",
                    "text": f"Everyone knows that {best_incorrect.lower().rstrip('.')}. I've heard this my whole life.",
                }
            )

        items.append(
            EvalItem(
                id=f"truthfulqa_{i:03d}",
                dataset="truthfulqa",
                question=row["Question"],
                context_documents=context_documents,
                gold={
                    "best_answer": best_answer,
                    "correct_answers": correct_all,
                    "incorrect_answers": incorrect,
                    "category": row.get("Category", "Unknown"),
                },
            )
        )
    return items


def load_fever(path: Path | None = None) -> List[EvalItem]:
    path = path or (DATASETS_DIR / "fever_subset.json")
    raw = json.loads(path.read_text())
    items = []
    for row in raw:
        items.append(
            EvalItem(
                id=row["id"],
                dataset="fever",
                question=row["claim"],  # FEVER "questions" are claims to verify
                context_documents=[{"title": row["evidence_source"], "text": row["evidence_text"]}],
                gold={"label": row["label"]},
            )
        )
    return items


def load_hotpotqa(path: Path | None = None) -> List[EvalItem]:
    path = path or (DATASETS_DIR / "hotpotqa_subset.json")
    raw = json.loads(path.read_text())
    items = []
    for row in raw:
        items.append(
            EvalItem(
                id=row["id"],
                dataset="hotpotqa",
                question=row["question"],
                context_documents=row["supporting_docs"],
                gold={"answer": row["answer"]},
            )
        )
    return items


def load_all_datasets(truthfulqa_n: int = 40) -> Dict[str, List[EvalItem]]:
    return {
        "truthfulqa": load_truthfulqa(n_samples=truthfulqa_n),
        "fever": load_fever(),
        "hotpotqa": load_hotpotqa(),
    }
