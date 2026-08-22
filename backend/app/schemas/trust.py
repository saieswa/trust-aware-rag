"""
Pydantic schemas for the Trust Score API.
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
        description="Pre-fetched evidence (e.g. from /agents/retriever/run). If omitted, runs the full Retriever + Critic pipeline first.",
    )
    method: ScoringMethodLiteral = Field(
        default="auto",
        description="'formula' always uses the hand-built formula; 'ml' uses the trained XGBoost model (falls back to formula if untrained); 'auto' uses ML if available, formula otherwise.",
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
    scoring_method: str = Field(..., description="'formula' or 'ml' — whichever actually produced this score.")
    # Dict[str, Any] rather than a fixed schema: the formula returns
    # {value, weight, contribution} per feature, the ML model returns a
    # single SHAP contribution value per feature — different shapes for a
    # genuinely different (but analogous) kind of explanation.
    feature_breakdown: Dict[str, Any]
    raw_features: Dict[str, float] = Field(..., description="The five raw trust features, always present regardless of scoring method.")
    diagnostics: Dict[str, int]
    contradictions: List[Dict[str, Any]]
    contradiction_method: str
    labeling_method: str
    evidence: List[Dict[str, Any]]


class TrustDashboardResponse(BaseModel):
    total_queries: int
    average_trust_score: float
    decision_counts: Dict[str, int]
    average_contradiction_score: float
    average_agreement_score: float
    llm_usage_rate: float = Field(..., description="Fraction of queries where the LLM (not heuristic fallback) was used.")


class TrainModelRequest(BaseModel):
    n_samples: int = Field(default=4000, ge=200, le=50000, description="Number of synthetic training rows to generate (ignored if csv_path is set).")
    csv_path: Optional[str] = Field(default=None, description="Path to a real labeled CSV dataset, if available. Falls back to synthetic data if omitted.")


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
