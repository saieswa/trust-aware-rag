"""
Node 5 — Label Evidence as Support / Contradict / Neutral.

Primary path: LLM, given the original question, every chunk, and the
already-detected contradiction pairs from Node 4 (so it doesn't have to
re-derive which chunks conflict — it only has to decide, for a conflicting
pair, which side is more trustworthy).

Fallback: deterministic rule combining three things already computed by
earlier nodes:
  - is this chunk part of a detected contradiction pair?
  - how does its quality_score compare to the chunk(s) it conflicts with?
  - is it relevant enough at all (using the retrieval similarity score
    already attached to the chunk) to be "support" rather than "neutral"?
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal

from loguru import logger
from pydantic import BaseModel, Field

from agents.llm_client import get_groq_llm
from agents.prompts.critic_prompts import (
    EVIDENCE_LABELING_SYSTEM_PROMPT,
    EVIDENCE_LABELING_USER_TEMPLATE,
)
from agents.state.critic_state import CriticState

# Below this quality score, a chunk is never labeled "support" even if
# nothing contradicts it — it's simply too vague/unreliable to rely on.
MIN_QUALITY_FOR_SUPPORT = 0.35
# Below this retrieval similarity score, a chunk is considered off-topic
# ("neutral") regardless of quality — it just doesn't answer the question.
MIN_RELEVANCE_FOR_SUPPORT = 0.15


class EvidenceLabel(BaseModel):
    chunk_id: str
    label: Literal["support", "contradict", "neutral"]
    reasoning: str = Field(description="One-sentence justification.")


class EvidenceLabelList(BaseModel):
    labels: List[EvidenceLabel]


def _llm_label_evidence(
    query: str, evidence: List[Dict[str, Any]], contradictions: List[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    llm = get_groq_llm(temperature=0, timeout=20)

    evidence_block = "\n".join(f"{c['chunk_id']}: {c['text']}" for c in evidence)
    contradiction_block = (
        "\n".join(f"- {c['chunk_id_a']} vs {c['chunk_id_b']}: {c['explanation']}" for c in contradictions)
        or "None detected."
    )

    structured_llm = llm.with_structured_output(EvidenceLabelList)
    result = structured_llm.invoke(
        [
            ("system", EVIDENCE_LABELING_SYSTEM_PROMPT),
            (
                "human",
                EVIDENCE_LABELING_USER_TEMPLATE.format(
                    query=query, evidence_block=evidence_block, contradiction_block=contradiction_block
                ),
            ),
        ]
    )
    return {label.chunk_id: label.model_dump() for label in result.labels}


def _heuristic_label_evidence(
    evidence: List[Dict[str, Any]],
    contradictions: List[Dict[str, Any]],
    quality_scores: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    # Build a lookup: chunk_id -> set of chunk_ids it contradicts.
    conflicts_with: Dict[str, List[str]] = {}
    for pair in contradictions:
        conflicts_with.setdefault(pair["chunk_id_a"], []).append(pair["chunk_id_b"])
        conflicts_with.setdefault(pair["chunk_id_b"], []).append(pair["chunk_id_a"])

    labels: Dict[str, Dict[str, Any]] = {}
    for chunk in evidence:
        chunk_id = chunk["chunk_id"]
        quality = quality_scores[chunk_id]["quality_score"]
        relevance = chunk.get("final_rank_score", chunk.get("score", 0.0))
        opponents = conflicts_with.get(chunk_id, [])

        if opponents:
            # Compare this chunk's quality against every chunk it conflicts
            # with; if any opponent is clearly more reliable, this one is
            # the "contradict" side. Otherwise (this chunk is the more
            # reliable side, or it's a tie) it's "support" — the report
            # still surfaces the conflict for transparency either way.
            opponent_qualities = [quality_scores[o]["quality_score"] for o in opponents if o in quality_scores]
            if opponent_qualities and quality < max(opponent_qualities):
                labels[chunk_id] = {
                    "chunk_id": chunk_id,
                    "label": "contradict",
                    "reasoning": (
                        f"Conflicts with more reliable evidence ({', '.join(opponents)}); "
                        f"quality_score={quality} is lower."
                    ),
                }
            else:
                labels[chunk_id] = {
                    "chunk_id": chunk_id,
                    "label": "support",
                    "reasoning": (
                        f"Conflicts with {', '.join(opponents)}, but this chunk has the "
                        f"higher (or equal) quality_score={quality}."
                    ),
                }
            continue

        if quality >= MIN_QUALITY_FOR_SUPPORT and relevance >= MIN_RELEVANCE_FOR_SUPPORT:
            labels[chunk_id] = {
                "chunk_id": chunk_id,
                "label": "support",
                "reasoning": f"No conflicts detected; quality_score={quality}, relevance={relevance:.2f}.",
            }
        else:
            labels[chunk_id] = {
                "chunk_id": chunk_id,
                "label": "neutral",
                "reasoning": f"Below support threshold (quality_score={quality}, relevance={relevance:.2f}).",
            }

    return labels


def label_evidence(state: CriticState) -> Dict[str, Any]:
    """LangGraph node: reads `normalized_evidence`, `contradictions`,
    `quality_scores`; writes `labels` and `labeling_method`."""
    query = state["original_query"]
    evidence = state["normalized_evidence"]
    contradictions = state["contradictions"]
    quality_scores = state["quality_scores"]

    try:
        labels = _llm_label_evidence(query, evidence, contradictions)
        if not labels:
            raise ValueError("LLM returned no labels.")
        method = "llm"
    except Exception as exc:
        logger.warning(f"LLM evidence labeling unavailable ({exc}); falling back to heuristic.")
        labels = _heuristic_label_evidence(evidence, contradictions, quality_scores)
        method = "heuristic"

    logger.info(f"Labeled {len(labels)} chunk(s) via {method}.")
    return {"labels": labels, "labeling_method": method}
