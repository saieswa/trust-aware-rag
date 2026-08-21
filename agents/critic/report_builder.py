"""
Final Node — Build Critic Report.

Combines every prior node's output into one structured JSON object: this
is the actual deliverable of the Critic Agent, and exactly what the
Synthesizer Agent (next project step) and the future Trust Model will
consume. Nothing downstream should ever need to re-read the raw
intermediate state — this report is self-contained.
"""

from __future__ import annotations

from typing import Any, Dict

from loguru import logger

from agents.state.critic_state import CriticState


def build_critic_report(state: CriticState) -> Dict[str, Any]:
    """LangGraph node: reads everything, writes `critic_report`."""
    evidence = state["normalized_evidence"]
    quality_scores = state["quality_scores"]
    labels = state["labels"]
    contradictions = state["contradictions"]

    per_chunk = []
    label_counts = {"support": 0, "contradict": 0, "neutral": 0}

    for chunk in evidence:
        chunk_id = chunk["chunk_id"]
        label_info = labels.get(chunk_id, {"label": "neutral", "reasoning": "No label produced."})
        label_counts[label_info["label"]] += 1

        per_chunk.append(
            {
                "chunk_id": chunk_id,
                "doc_id": chunk.get("doc_id"),
                "source_title": chunk.get("source_title"),
                "text": chunk["text"],
                "label": label_info["label"],
                "reasoning": label_info["reasoning"],
                # Carried forward from the Retriever Agent's output so the
                # Trust Score system (a later step) can compute a
                # similarity feature without needing to re-fetch anything.
                "score": chunk.get("score", 0.0),
                "final_rank_score": chunk.get("final_rank_score", chunk.get("score", 0.0)),
                **quality_scores.get(chunk_id, {}),
            }
        )

    total = len(evidence) or 1  # avoid division by zero
    agreement_rate = round(label_counts["support"] / total, 3)
    contradiction_ratio = round(len(contradictions) / total, 3)
    average_quality = round(sum(c["quality_score"] for c in quality_scores.values()) / (len(quality_scores) or 1), 3)

    critic_report = {
        "original_query": state["original_query"],
        "evidence_count": len(evidence),
        "label_counts": label_counts,
        "agreement_rate": agreement_rate,
        "contradiction_ratio": contradiction_ratio,
        "average_quality_score": average_quality,
        "contradictions": contradictions,
        "contradiction_method": state.get("contradiction_method", "none"),
        "labeling_method": state.get("labeling_method", "none"),
        "evidence": per_chunk,
    }

    logger.info(
        f"Critic report built — {label_counts} | agreement_rate={agreement_rate} "
        f"contradiction_ratio={contradiction_ratio} avg_quality={average_quality}"
    )
    return {"critic_report": critic_report}
