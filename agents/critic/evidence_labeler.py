"""
Node 5 — Label Evidence as Support / Contradict / Neutral (Irrelevant).

Primary path: LLM evaluations against the query.
Fallback: Strict heuristic rules requiring semantic relevance or document-level coverage.
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

# Below this quality score, a chunk is never labeled "support"
MIN_QUALITY_FOR_SUPPORT = 0.35
# Below this relevance score, a chunk is off-topic ("neutral" / "irrelevant")
MIN_RELEVANCE_FOR_SUPPORT = 0.25


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

    evidence_block = "\n".join(
        f"{c['chunk_id']} [Section: {c.get('section', 'General')} | Score: {c.get('final_rank_score', c.get('score', 0.0))}]: {c['text']}"
        for c in evidence
    )
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
    conflicts_with: Dict[str, List[str]] = {}
    for pair in contradictions:
        conflicts_with.setdefault(pair["chunk_id_a"], []).append(pair["chunk_id_b"])
        conflicts_with.setdefault(pair["chunk_id_b"], []).append(pair["chunk_id_a"])

    labels: Dict[str, Dict[str, Any]] = {}
    for chunk in evidence:
        chunk_id = chunk["chunk_id"]
        quality = quality_scores.get(chunk_id, {}).get("quality_score", 0.5)
        relevance = chunk.get("final_rank_score", chunk.get("score", 0.0))
        opponents = conflicts_with.get(chunk_id, [])

        if opponents:
            opponent_qualities = [quality_scores[o]["quality_score"] for o in opponents if o in quality_scores]
            if opponent_qualities and quality < max(opponent_qualities):
                labels[chunk_id] = {
                    "chunk_id": chunk_id,
                    "label": "contradict",
                    "reasoning": f"Conflicts with higher quality evidence ({', '.join(opponents)}).",
                }
            else:
                labels[chunk_id] = {
                    "chunk_id": chunk_id,
                    "label": "support",
                    "reasoning": f"Conflicts with {', '.join(opponents)}, but has higher quality score ({quality}).",
                }
            continue

        if relevance >= 0.70 or (quality >= MIN_QUALITY_FOR_SUPPORT and relevance >= MIN_RELEVANCE_FOR_SUPPORT):
            labels[chunk_id] = {
                "chunk_id": chunk_id,
                "label": "support",
                "reasoning": f"Relevant evidence from active document (relevance={relevance:.2f}, quality={quality:.2f}).",
            }
        else:
            labels[chunk_id] = {
                "chunk_id": chunk_id,
                "label": "neutral",
                "reasoning": f"Insufficient relevance or quality to support claim (relevance={relevance:.2f}, quality={quality:.2f}).",
            }

    return labels


def label_evidence(state: CriticState) -> Dict[str, Any]:
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
        logger.warning(f"LLM evidence labeling unavailable ({exc}); using strict heuristic.")
        labels = _heuristic_label_evidence(evidence, contradictions, quality_scores)
        method = "heuristic"

    logger.info(f"Labeled {len(labels)} chunk(s) via {method}.")
    return {"labels": labels, "labeling_method": method}
