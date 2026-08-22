"""
Trust Service.

Wraps trust/trust_engine.py for API use, and persists every computed trust
report as a TrustScoreLog row — this is what makes the Trust Dashboard API
possible. Also exposes model training and model info for the ML trust
model (trust/model/trust_model.py, trust/training/train_trust_model.py).
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ServiceUnavailableError
from app.schemas.trust import (
    ModelInfoResponse,
    TrainModelResponse,
    TrustDashboardResponse,
    TrustReportResponse,
)
from database.postgres.models.trust_score_log import TrustScoreLog
from trust.model.trust_model import get_trust_ml_model, reset_trust_ml_model_cache
from trust.trust_engine import compute_trust_report


class TrustService:
    async def score_query(
        self,
        db: AsyncSession,
        query: str,
        k: int,
        evidence: Optional[List[Dict[str, Any]]],
        method: str = "auto",
        doc_id: Optional[str] = None,
    ) -> TrustReportResponse:
        from app.services.cache_service import get_cache_service
        cache_service = get_cache_service()
        effective_doc_id = doc_id or await cache_service.get_active_document_id()

        if not effective_doc_id and evidence is None:
            return TrustReportResponse(
                query=query,
                doc_id=None,
                trust_score=0.0,
                decision="abstain",
                feature_breakdown={},
                diagnostics={
                    "evidence_count": 0,
                    "support_count": 0,
                    "distinct_source_count": 0,
                    "contradiction_count": 0,
                },
                contradictions=[],
                contradiction_method="none",
                labeling_method="none",
                evidence=[],
            )

        if effective_doc_id and evidence is None:
            cached_data = await cache_service.get_cached("trust", effective_doc_id, query)
            if cached_data:
                return TrustReportResponse(**cached_data)

        try:
            report = compute_trust_report(
                query=query,
                k=k,
                evidence=evidence,
                method=method,
                doc_id=effective_doc_id,
            )
            report["doc_id"] = effective_doc_id
        except Exception as exc:
            raise ServiceUnavailableError(f"Trust scoring failed: {exc}") from exc

        await self._persist(db, report)

        response = TrustReportResponse(**report)
        if effective_doc_id and evidence is None:
            await cache_service.set_cached("trust", effective_doc_id, query, response.model_dump())

        return response

    async def _persist(self, db: AsyncSession, report: Dict[str, Any]) -> None:
        """Writes one row per trust score computation. Failures here are
        logged but never raised — a dashboard-logging failure should not
        cause the actual trust score response to fail."""
        from loguru import logger

        try:
            raw_features = report["raw_features"]
            diagnostics = report["diagnostics"]

            log_row = TrustScoreLog(
                query=report["query"],
                trust_score=report["trust_score"],
                decision=report["decision"],
                scoring_method=report.get("scoring_method", "formula"),
                agreement_score=raw_features["agreement_score"],
                source_reliability=raw_features["source_reliability"],
                similarity_score=raw_features["similarity_score"],
                contradiction_score=raw_features["contradiction_score"],
                source_count_score=raw_features["source_count_score"],
                evidence_count=diagnostics["evidence_count"],
                support_count=diagnostics["support_count"],
                distinct_source_count=diagnostics["distinct_source_count"],
                contradiction_count=diagnostics["contradiction_count"],
                contradiction_method=report["contradiction_method"],
                labeling_method=report["labeling_method"],
            )
            db.add(log_row)
            await db.commit()
        except Exception as exc:
            logger.warning(f"Failed to persist trust score log (non-fatal): {exc}")
            await db.rollback()

    async def dashboard_stats(self, db: AsyncSession) -> TrustDashboardResponse:
        """
        Aggregates over every logged trust score computation:
          - total queries evaluated
          - average trust score
          - decision breakdown (answer / retrieve_more / abstain counts)
          - average contradiction ratio
          - how often the LLM path vs. heuristic fallback was used
        """
        total_result = await db.execute(select(func.count(TrustScoreLog.id)))
        total_queries = total_result.scalar_one()

        if total_queries == 0:
            return TrustDashboardResponse(
                total_queries=0,
                average_trust_score=0.0,
                decision_counts={"answer": 0, "retrieve_more": 0, "abstain": 0},
                average_contradiction_score=0.0,
                average_agreement_score=0.0,
                llm_usage_rate=0.0,
            )

        avg_result = await db.execute(
            select(
                func.avg(TrustScoreLog.trust_score),
                func.avg(TrustScoreLog.contradiction_score),
                func.avg(TrustScoreLog.agreement_score),
            )
        )
        avg_trust, avg_contradiction, avg_agreement = avg_result.one()

        decision_result = await db.execute(
            select(TrustScoreLog.decision, func.count(TrustScoreLog.id)).group_by(TrustScoreLog.decision)
        )
        decision_counts = {"answer": 0, "retrieve_more": 0, "abstain": 0}
        for decision, count in decision_result.all():
            decision_counts[decision] = count

        llm_result = await db.execute(
            select(func.count(TrustScoreLog.id)).where(TrustScoreLog.labeling_method == "llm")
        )
        llm_count = llm_result.scalar_one()

        return TrustDashboardResponse(
            total_queries=total_queries,
            average_trust_score=round(float(avg_trust), 4),
            decision_counts=decision_counts,
            average_contradiction_score=round(float(avg_contradiction), 4),
            average_agreement_score=round(float(avg_agreement), 4),
            llm_usage_rate=round(llm_count / total_queries, 4),
        )

    def train_model(self, n_samples: int, csv_path: Optional[str]) -> TrainModelResponse:
        """Runs the full XGBoost training pipeline synchronously (fast —
        a few seconds on a few thousand synthetic rows) and resets the
        cached inference model so the very next trust score request picks
        up the freshly trained one."""
        from trust.training.train_trust_model import train_trust_model

        try:
            metadata = train_trust_model(csv_path=csv_path, n_samples=n_samples)
        except Exception as exc:
            raise ServiceUnavailableError(f"Model training failed: {exc}") from exc

        reset_trust_ml_model_cache()
        return TrainModelResponse(**metadata)

    def model_info(self) -> ModelInfoResponse:
        model = get_trust_ml_model()
        if model is None:
            return ModelInfoResponse(trained=False)

        return ModelInfoResponse(
            trained=True,
            trained_at=model.metadata.get("trained_at"),
            test_metrics=model.metadata.get("test_metrics"),
            formula_baseline_metrics=model.metadata.get("formula_baseline_metrics"),
            feature_importances=model.metadata.get("feature_importances"),
            n_samples=model.metadata.get("n_samples"),
        )


_service_singleton: Optional[TrustService] = None


def get_trust_service() -> TrustService:
    global _service_singleton
    if _service_singleton is None:
        _service_singleton = TrustService()
    return _service_singleton
