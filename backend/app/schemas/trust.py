"""
Pydantic schemas for the Trust Score & Dashboard API.
"""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

ScoringMethodLiteral = Literal["formula", "ml", "auto"]


class TrustScoreRequest(BaseModel):
    query: str = Field(..., min_length=1, examples=["Is it safe to combine Drug X and Drug Y?"])
    k: int = Field(default=5, ge=1, le=20)
    doc_id: Optional[str] = Field(default=None, description="Active document ID to scope retrieval and trust scoring.")
    evidence: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Pre-fetched evidence. If omitted, runs the full Retriever + Critic pipeline first.",
    )
    method: ScoringMethodLiteral = Field(
        default="auto",
        description="'formula' always uses the formula; 'ml' uses the trained XGBoost model; 'auto' uses ML if available.",
    )


class FeatureDetail(BaseModel):
    value: float
    weight: float
    contribution: float
    applied_as: Optional[str] = None


class TrustReportResponse(BaseModel):
    query: str
    doc_id: Optional[str] = None
    trust_score: float = Field(..., description="Final trust score, 0.0-1.0.")
    decision: str = Field(..., description="'answer', 'retrieve_more', or 'abstain'.")
    scoring_method: str = Field(..., description="'formula' or 'ml'.")
    feature_breakdown: Dict[str, Any]
    raw_features: Dict[str, float] = Field(..., description="The five raw trust features.")
    diagnostics: Dict[str, int]
    contradictions: List[Dict[str, Any]]
    contradiction_method: str
    labeling_method: str
    evidence: List[Dict[str, Any]]


class EvaluationHistoryItem(BaseModel):
    id: str
    query: str
    doc_id: Optional[str] = None
    document_name: str
    decision: str
    trust_score: float
    created_at: str
    final_answer: Optional[str] = None


class DocumentPerformanceItem(BaseModel):
    doc_id: str
    document_name: str
    total_queries: int
    average_trust_score: float
    supported_count: int
    needs_more_evidence_count: int
    abstained_count: int


class TrustDashboardResponse(BaseModel):
    total_queries: int
    average_trust_score: float
    decision_counts: Dict[str, int]
    average_contradiction_score: float
    average_agreement_score: float
    llm_usage_rate: float = Field(..., description="Fraction of queries where the LLM (not heuristic fallback) was used.")
    history: List[EvaluationHistoryItem] = Field(default_factory=list)
    document_performance: List[DocumentPerformanceItem] = Field(default_factory=list)


class TrainModelRequest(BaseModel):
    n_samples: int = Field(default=4000, ge=200, le=50000)
    csv_path: Optional[str] = None


class TrainModelResponse(BaseModel):
    trained_at: str
    n_samples: int
    train_size: int
    val_size: int
    test_size: int
    best_iteration: int
    features: List[str]
    test_metrics: Dict[str, float]
    formula_baseline_metrics: Dict[str, float]
    feature_importances: Dict[str, float]
    model_path: str
    data_source: str


class ModelInfoResponse(BaseModel):
    trained: bool
    trained_at: Optional[str] = None
    test_metrics: Optional[Dict[str, float]] = None
    formula_baseline_metrics: Optional[Dict[str, float]] = None
    feature_importances: Optional[Dict[str, float]] = None
    n_samples: Optional[int] = None
