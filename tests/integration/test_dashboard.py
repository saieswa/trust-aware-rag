import pytest
from app.services.trust_service import get_trust_service
from database.postgres.session import get_session_context
from database.postgres.models.trust_score_log import TrustScoreLog


@pytest.mark.asyncio
async def test_dashboard_metrics_and_history():
    trust_service = get_trust_service()

    async with get_session_context() as db:
        # Create test log entries for Document A
        log_a1 = TrustScoreLog(
            query="What is the title of Paper A?",
            doc_id="doc_test_a",
            document_name="Paper_A.pdf",
            trust_score=0.92,
            decision="answer",
            scoring_method="formula",
            agreement_score=0.90,
            source_reliability=0.95,
            similarity_score=0.88,
            contradiction_score=0.0,
            source_count_score=0.80,
            evidence_count=3,
            support_count=3,
            distinct_source_count=1,
            contradiction_count=0,
        )
        log_a2 = TrustScoreLog(
            query="What is the method in Paper A?",
            doc_id="doc_test_a",
            document_name="Paper_A.pdf",
            trust_score=0.45,
            decision="retrieve_more",
            scoring_method="formula",
            agreement_score=0.40,
            source_reliability=0.95,
            similarity_score=0.50,
            contradiction_score=0.0,
            source_count_score=0.80,
            evidence_count=2,
            support_count=1,
            distinct_source_count=1,
            contradiction_count=0,
        )

        # Create test log entry for Document B
        log_b1 = TrustScoreLog(
            query="What is the recipe for cake in Paper B?",
            doc_id="doc_test_b",
            document_name="Paper_B.pdf",
            trust_score=0.15,
            decision="abstain",
            scoring_method="formula",
            agreement_score=0.10,
            source_reliability=0.90,
            similarity_score=0.10,
            contradiction_score=0.0,
            source_count_score=0.50,
            evidence_count=1,
            support_count=0,
            distinct_source_count=1,
            contradiction_count=0,
        )

        db.add_all([log_a1, log_a2, log_b1])
        await db.commit()

        # Fetch dashboard statistics
        stats = await trust_service.dashboard_stats(db)

        # 1. Total queries must be positive
        assert stats.total_queries >= 3

        # 2. Supported + Needs More Evidence + Abstained must equal total queries
        sum_decisions = (
            stats.decision_counts.get("answer", 0)
            + stats.decision_counts.get("retrieve_more", 0)
            + stats.decision_counts.get("abstain", 0)
        )
        assert sum_decisions == stats.total_queries

        # 3. Average trust score must be bounded
        assert 0.0 <= stats.average_trust_score <= 1.0

        # 4. History records must be returned with document association
        assert len(stats.history) > 0
        queries_in_history = [h.query for h in stats.history]
        assert "What is the title of Paper A?" in queries_in_history

        # 5. Document performance must isolate documents
        doc_names = [d.document_name for d in stats.document_performance]
        assert "Paper_A.pdf" in doc_names
        assert "Paper_B.pdf" in doc_names

        # Verify Document A specific metrics
        doc_a_perf = next(d for d in stats.document_performance if d.document_name == "Paper_A.pdf")
        assert doc_a_perf.total_queries >= 2
        assert doc_a_perf.supported_count >= 1
        assert doc_a_perf.needs_more_evidence_count >= 1
