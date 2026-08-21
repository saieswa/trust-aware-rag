"""
Pydantic schemas for the Critic Agent API.
"""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class CriticAgentRequest(BaseModel):
    query: str = Field(..., min_length=1, examples=["Is it safe to combine Drug X and Drug Y?"])
    k: int = Field(default=5, ge=1, le=20, description="Used only if `evidence` is omitted — runs the Retriever Agent first.")
    evidence: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Pre-fetched evidence chunks (e.g. from /agents/retriever/run). If omitted, the Retriever Agent runs first.",
    )


class ContradictionResponse(BaseModel):
    chunk_id_a: str
    chunk_id_b: str
    explanation: str


class ScoredEvidenceResponse(BaseModel):
    chunk_id: str
    doc_id: str
    source_title: str
    text: str
    label: Literal["support", "contradict", "neutral"]
    reasoning: str
    score: float = Field(..., description="Raw retrieval similarity score.")
    final_rank_score: float = Field(..., description="Retriever Agent's ranked score (similarity + agreement bonus).")
    specificity_score: float
    source_reliability_score: float
    quality_score: float


class CriticAgentResponse(BaseModel):
    original_query: str
    evidence_count: int
    label_counts: Dict[str, int]
    agreement_rate: float = Field(..., description="Fraction of evidence labeled 'support'.")
    contradiction_ratio: float = Field(..., description="Contradiction pairs relative to evidence count.")
    average_quality_score: float
    contradictions: List[ContradictionResponse]
    contradiction_method: str = Field(..., description="'llm', 'heuristic', or 'none'.")
    labeling_method: str = Field(..., description="'llm' or 'heuristic'.")
    evidence: List[ScoredEvidenceResponse]
