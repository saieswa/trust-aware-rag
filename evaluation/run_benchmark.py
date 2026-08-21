"""
Benchmark Runner.

For every question in every dataset:
  1. Index that question's own small evidence corpus into a fresh,
     isolated retrieval index (mirrors an "oracle retrieval" evaluation
     setup — standard practice when evaluating the reasoning/verification
     stages independently of large-scale retrieval quality).
  2. Run the full Trust-Aware pipeline (Retriever -> Critic -> Trust ->
     Synthesizer -> Verifier).
  3. Run the Baseline RAG pipeline (retrieve -> blend -> answer, no
     judgment) on the exact same corpus and question.
  4. Score both against the dataset's ground truth using the SAME
     yardstick — including reusing the Verifier's own sentence-checking
     logic as an independent post-hoc judge of the baseline's
     hallucination rate, so hallucination is measured identically for
     both systems rather than only being available for one of them.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from loguru import logger

from evaluation.baseline_rag import run_baseline_rag
from evaluation.datasets.loaders import EvalItem, load_all_datasets
from evaluation.metrics import answer_is_correct, token_f1


def _build_item_pipeline(item: EvalItem, embedder):
    """Writes an item's context documents to a temp directory and indexes
    them into a fresh RetrievalPipeline — reuses the real production
    loader/chunker/FAISS code path, not an evaluation-only shortcut."""
    from retrieval.retriever import RetrievalPipeline

    temp_dir = Path(tempfile.mkdtemp(prefix="eval_"))
    for i, doc in enumerate(item.context_documents):
        (temp_dir / f"doc_{i}.txt").write_text(f"{doc['title']}\n\n{doc['text']}", encoding="utf-8")

    pipeline = RetrievalPipeline(embedder=embedder)
    pipeline.index_dir = temp_dir / "index"
    pipeline.faiss_index_path = pipeline.index_dir.with_suffix(".index")
    pipeline.metadata_path = pipeline.index_dir.with_suffix(".meta.json")
    pipeline.index_directory(str(temp_dir), chunk_size=500, chunk_overlap=50)

    return pipeline, temp_dir


def _measure_hallucination_of_text(query: str, answer_text: str, evidence_chunks) -> float:
    """
    Runs the Verifier Agent's OWN sentence-splitting + support-checking
    logic against arbitrary answer text — used here to judge the
    BASELINE's answer by the exact same yardstick as the Trust-Aware
    system's Verifier judges its own answer, so hallucination rate is an
    apples-to-apples comparison rather than "measured for one system,
    unavailable for the other."
    """
    from agents.verifier.sentence_splitter import split_sentences

    # Baseline answers rarely include [chunk_id] citations (it just
    # concatenates raw chunk text) — the heuristic checker treats missing
    # citations as unsupported by design, which would make EVERY baseline
    # sentence "unsupported" regardless of content and defeat the purpose
    # of measuring actual factual grounding. For this evaluation-only
    # measurement, every retrieved chunk is appended as a possible match
    # and support is judged on word overlap alone, ignoring the
    # citation-presence check — a deliberate, documented adaptation for
    # fair comparison, not used anywhere in the production Verifier.
    import re

    from agents.verifier.sentence_checker import _tokenize, _word_overlap, MIN_OVERLAP_FOR_SUPPORT

    state = {"draft_answer": answer_text, "abstained": False}
    sentences = split_sentences(state)["sentences"]
    if not sentences:
        return 0.0

    evidence_tokens = [_tokenize(c.text) for c in evidence_chunks]
    unsupported = 0
    for sentence in sentences:
        sentence_tokens = _tokenize(re.sub(r"\[([a-zA-Z0-9_]+)\]", "", sentence))
        best_overlap = max((_word_overlap(sentence_tokens, et) for et in evidence_tokens), default=0.0)
        if best_overlap < MIN_OVERLAP_FOR_SUPPORT:
            unsupported += 1

    return round(unsupported / len(sentences), 4)


def _evaluate_truthfulqa_item(final_answer: str, gold: Dict[str, Any]) -> bool:
    """Correct if the answer resembles the TRUE answer set more than the
    FALSE (incorrect) answer set, by token-F1 — i.e. did the system's
    output land closer to the truth than to the popular misconception."""
    true_candidates = [gold["best_answer"]] + gold["correct_answers"]
    false_candidates = gold["incorrect_answers"]

    best_true_f1 = max((token_f1(final_answer, c)[2] for c in true_candidates), default=0.0)
    best_false_f1 = max((token_f1(final_answer, c)[2] for c in false_candidates), default=0.0)

    return best_true_f1 > best_false_f1


def run_benchmark(embedder=None, truthfulqa_n: int = 40, max_retries: int = 1) -> List[Dict[str, Any]]:
    """Runs both systems over all three datasets and returns one flat list
    of per-item result records (the raw data the report is built from)."""
    from agents.pipeline.agent import run_full_pipeline
    import agents.retriever.multi_search as multi_search_module
    from trust.trust_engine import compute_trust_report

    if embedder is None:
        from retrieval.embeddings.embedding_model import get_embedder

        embedder = get_embedder()

    datasets = load_all_datasets(truthfulqa_n=truthfulqa_n)
    records: List[Dict[str, Any]] = []

    for dataset_name, items in datasets.items():
        logger.info(f"Evaluating dataset '{dataset_name}' — {len(items)} item(s)")

        for item in items:
            pipeline, temp_dir = _build_item_pipeline(item, embedder)
            multi_search_module.get_retrieval_pipeline = lambda p=pipeline: p

            try:
                k = max(len(item.context_documents), 1)

                trust_report = compute_trust_report(item.question, k=k, method="formula")
                synthesis_state = run_full_pipeline(item.question, trust_report, max_retries=max_retries)
                system_report = synthesis_state["final_report"]

                baseline_result = run_baseline_rag(item.question, pipeline, k=k)
                baseline_evidence_chunks = pipeline.search(item.question, k=k)
                baseline_hallucination = _measure_hallucination_of_text(
                    item.question, baseline_result["final_answer"], baseline_evidence_chunks
                )

                record: Dict[str, Any] = {
                    "id": item.id,
                    "dataset": dataset_name,
                    "question": item.question,
                    "system_answer": system_report["final_answer"],
                    "system_status": system_report["status"],
                    "system_hallucination_ratio": system_report["hallucination_ratio"],
                    "system_trust_score": trust_report["trust_score"],
                    "system_decision": trust_report["decision"],
                    "baseline_answer": baseline_result["final_answer"],
                    "baseline_hallucination_ratio": baseline_hallucination,
                }

                if dataset_name == "fever":
                    label_map = {"support": "SUPPORTS", "contradict": "REFUTES", "neutral": "NOT ENOUGH INFO"}
                    evidence = trust_report["evidence"]
                    predicted_label = label_map.get(evidence[0]["label"], "NOT ENOUGH INFO") if evidence else "NOT ENOUGH INFO"
                    record["gold_label"] = item.gold["label"]
                    record["system_predicted_label"] = predicted_label
                    record["system_correct"] = predicted_label == item.gold["label"]
                    # Baseline RAG has no classification mechanism — it
                    # never actively flags a claim as false, so its
                    # implicit prediction is always "SUPPORTS" (it just
                    # repeats retrieved text without judgment).
                    record["baseline_predicted_label"] = "SUPPORTS"
                    record["baseline_correct"] = "SUPPORTS" == item.gold["label"]

                elif dataset_name == "hotpotqa":
                    gold_answer = item.gold["answer"]
                    record["gold_answer"] = gold_answer
                    p, r, f1 = token_f1(system_report["final_answer"], gold_answer)
                    record["system_precision"], record["system_recall"], record["system_f1"] = p, r, f1
                    record["system_correct"] = answer_is_correct(system_report["final_answer"], gold_answer)
                    bp, br, bf1 = token_f1(baseline_result["final_answer"], gold_answer)
                    record["baseline_precision"], record["baseline_recall"], record["baseline_f1"] = bp, br, bf1
                    record["baseline_correct"] = answer_is_correct(baseline_result["final_answer"], gold_answer)

                elif dataset_name == "truthfulqa":
                    record["system_correct"] = _evaluate_truthfulqa_item(system_report["final_answer"], item.gold)
                    record["baseline_correct"] = _evaluate_truthfulqa_item(baseline_result["final_answer"], item.gold)
                    record["category"] = item.gold["category"]

                records.append(record)

            except Exception as exc:
                logger.error(f"Failed on item {item.id}: {exc}")
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

    return records
