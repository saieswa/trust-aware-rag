"""
Trust Service.

Wraps trust/trust_engine.py for API use, and persists every computed trust
report as a TrustScoreLog row with document association. Aggregates real metrics,
evaluation history, and document-level performance for the Trust Dashboard.
"""

from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ServiceUnavailableError
from app.schemas.trust import (
    DocumentPerformanceItem,
    EvaluationHistoryItem,
    ModelInfoResponse,
    TrainModelResponse,
    TrustDashboardResponse,
    TrustReportResponse,
)
from database.postgres.models.document import DocumentRecord
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
                scoring_method="formula",
                feature_breakdown={},
                raw_features={
                    "agreement_score": 0.0,
                    "source_reliability": 0.0,
                    "similarity_score": 0.0,
                    "contradiction_score": 0.0,
                    "source_count_score": 0.0,
                },
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

        await self._persist(db, report, doc_id=effective_doc_id)

        response = TrustReportResponse(**report)
        if effective_doc_id and evidence is None:
            await cache_service.set_cached("trust", effective_doc_id, query, response.model_dump())

        return response

    async def _persist(
        self,
        db: AsyncSession,
        report: Dict[str, Any],
        doc_id: Optional[str] = None,
        final_answer: Optional[str] = None,
    ) -> None:
        """Writes one row per trust score computation with document association."""
        try:
            raw_features = report.get("raw_features", {})
            diagnostics = report.get("diagnostics", {})
            target_doc_id = doc_id or report.get("doc_id")

            doc_name = "Document"
            if target_doc_id:
                doc_res = await db.execute(
                    select(DocumentRecord.filename).where(DocumentRecord.doc_id == target_doc_id)
                )
                fetched_name = doc_res.scalar_one_or_none()
                if fetched_name:
                    doc_name = fetched_name
                else:
                    doc_name = target_doc_id

            log_row = TrustScoreLog(
                query=report["query"],
                doc_id=target_doc_id,
                document_name=doc_name,
                trust_score=report["trust_score"],
                decision=report["decision"],
                scoring_method=report.get("scoring_method", "formula"),
                final_answer=final_answer,
                agreement_score=raw_features.get("agreement_score", 0.0),
                source_reliability=raw_features.get("source_reliability", 0.0),
                similarity_score=raw_features.get("similarity_score", 0.0),
                contradiction_score=raw_features.get("contradiction_score", 0.0),
                source_count_score=raw_features.get("source_count_score", 0.0),
                evidence_count=diagnostics.get("evidence_count", 0),
                support_count=diagnostics.get("support_count", 0),
                distinct_source_count=diagnostics.get("distinct_source_count", 0),
                contradiction_count=diagnostics.get("contradiction_count", 0),
                contradiction_method=report.get("contradiction_method", "none"),
                labeling_method=report.get("labeling_method", "none"),
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
          - average agreement score
          - how often the LLM path vs. heuristic fallback was used
          - historical evaluation records
          - document-wise performance breakdown
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
                history=[],
                document_performance=[],
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

        # Fetch recent historical evaluation records (ordered by created_at desc)
        history_result = await db.execute(
            select(TrustScoreLog).order_by(TrustScoreLog.created_at.desc()).limit(150)
        )
        logs = history_result.scalars().all()

        # Fetch document name mappings
        doc_map_res = await db.execute(select(DocumentRecord.doc_id, DocumentRecord.filename))
        doc_names = {row[0]: row[1] for row in doc_map_res.all()}

        history_items: List[EvaluationHistoryItem] = []
        doc_perf_map: Dict[str, Dict[str, Any]] = {}

        for log in logs:
            doc_id = log.doc_id or "default"
            doc_name = log.document_name or doc_names.get(doc_id, "Active Document")

            created_iso = log.created_at.isoformat() if log.created_at else ""

            history_items.append(
                EvaluationHistoryItem(
                    id=str(log.id),
                    query=log.query,
                    doc_id=log.doc_id,
                    document_name=doc_name,
                    decision=log.decision,
                    trust_score=round(log.trust_score, 4),
                    created_at=created_iso,
                    final_answer=log.final_answer,
                )
            )

            # Accumulate Document Performance
            if doc_name not in doc_perf_map:
                doc_perf_map[doc_name] = {
                    "doc_id": doc_id,
                    "document_name": doc_name,
                    "total_queries": 0,
                    "trust_scores": [],
                    "supported_count": 0,
                    "needs_more_evidence_count": 0,
                    "abstained_count": 0,
                }

            entry = doc_perf_map[doc_name]
            entry["total_queries"] += 1
            entry["trust_scores"].append(log.trust_score)
            if log.decision == "answer":
                entry["supported_count"] += 1
            elif log.decision == "retrieve_more":
                entry["needs_more_evidence_count"] += 1
            else:
                entry["abstained_count"] += 1

        # Format Document Performance Items
        document_performance: List[DocumentPerformanceItem] = []
        for name, entry in doc_perf_map.items():
            avg_doc_trust = sum(entry["trust_scores"]) / len(entry["trust_scores"]) if entry["trust_scores"] else 0.0
            document_performance.append(
                DocumentPerformanceItem(
                    doc_id=entry["doc_id"],
                    document_name=name,
                    total_queries=entry["total_queries"],
                    average_trust_score=round(avg_doc_trust, 4),
                    supported_count=entry["supported_count"],
                    needs_more_evidence_count=entry["needs_more_evidence_count"],
                    abstained_count=entry["abstained_count"],
                )
            )

        return TrustDashboardResponse(
            total_queries=total_queries,
            average_trust_score=round(float(avg_trust or 0.0), 4),
            decision_counts=decision_counts,
            average_contradiction_score=round(float(avg_contradiction or 0.0), 4),
            average_agreement_score=round(float(avg_agreement or 0.0), 4),
            llm_usage_rate=round(llm_count / total_queries, 4) if total_queries > 0 else 0.0,
            history=history_items,
            document_performance=document_performance,
        )

    def train_model(self, n_samples: int, csv_path: Optional[str]) -> TrainModelResponse:
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
