"""
Trust Score API routes.

    POST /api/v1/trust/score        — compute (and log) a trust report for one query
    GET  /api/v1/trust/dashboard    — aggregate stats across every logged trust score
    POST /api/v1/trust/model/train  — train the XGBoost trust model
    GET  /api/v1/trust/model/info   — info about the currently trained model, if any
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.database import get_db
from app.schemas.trust import (
    ModelInfoResponse,
    TrainModelRequest,
    TrainModelResponse,
    TrustDashboardResponse,
    TrustReportResponse,
    TrustScoreRequest,
)
from app.services.trust_service import TrustService, get_trust_service

router = APIRouter(prefix="/trust", tags=["Trust Score"])


@router.post(
    "/score",
    response_model=TrustReportResponse,
    summary="Compute a trust score for a query",
    description=(
        "Runs the Retriever + Critic agents (unless `evidence` is supplied), "
        "extracts the five trust features, scores them via the hand-built "
        "formula or the trained XGBoost model (`method`: 'formula' | 'ml' | "
        "'auto'), logs the result, and returns the full structured report."
    ),
)
async def score_query(
    request: TrustScoreRequest,
    db: AsyncSession = Depends(get_db),
    service: TrustService = Depends(get_trust_service),
) -> TrustReportResponse:
    return await service.score_query(
        db,
        query=request.query,
        k=request.k,
        evidence=request.evidence,
        method=request.method,
        doc_id=request.doc_id,
    )


@router.get(
    "/dashboard",
    response_model=TrustDashboardResponse,
    summary="Trust score dashboard statistics",
    description=(
        "Aggregates every logged trust score computation: total queries "
        "evaluated, average trust score, decision breakdown, average "
        "contradiction/agreement scores, and how often the LLM path (vs. "
        "heuristic fallback) was used."
    ),
)
async def dashboard(
    db: AsyncSession = Depends(get_db),
    service: TrustService = Depends(get_trust_service),
) -> TrustDashboardResponse:
    return await service.dashboard_stats(db)


@router.post(
    "/model/train",
    response_model=TrainModelResponse,
    summary="Train the XGBoost trust model",
    description=(
        "Runs the full training pipeline: loads a dataset (synthetic by "
        "default, or a real labeled CSV via `csv_path`), engineers "
        "features, splits into train/validation/test, trains an XGBoost "
        "regressor with early stopping, evaluates against a held-out test "
        "set AND against the hand-built formula baseline, saves the model "
        "and metadata to disk, and returns the full training report."
    ),
)
async def train_model(
    request: TrainModelRequest,
    service: TrustService = Depends(get_trust_service),
) -> TrainModelResponse:
    return service.train_model(n_samples=request.n_samples, csv_path=request.csv_path)


@router.get(
    "/model/info",
    response_model=ModelInfoResponse,
    summary="Trained trust model info",
    description="Returns metadata about the currently trained XGBoost trust model, if one exists.",
)
async def model_info(
    service: TrustService = Depends(get_trust_service),
) -> ModelInfoResponse:
    return service.model_info()
