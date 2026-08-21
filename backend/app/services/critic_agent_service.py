"""
Critic Agent Service.

If the caller already has evidence (e.g. from a prior /agents/retriever/run
call), we critique it directly. Otherwise, this composes the two agents:
run the Retriever Agent first to get evidence, then hand it to the Critic
Agent — this is the same composition the future end-to-end pipeline
(Synthesizer/Verifier) will use.
"""

from typing import Any, Dict, List, Optional

from app.core.exceptions import ServiceUnavailableError
from app.schemas.critic_agent import (
    ContradictionResponse,
    CriticAgentResponse,
    ScoredEvidenceResponse,
)
from agents.critic.agent import run_critic_agent
from agents.retriever.agent import run_retriever_agent


class CriticAgentService:
    def run(self, query: str, k: int, evidence: Optional[List[Dict[str, Any]]]) -> CriticAgentResponse:
        try:
            if evidence is None:
                retriever_state = run_retriever_agent(query, k=k)
                evidence = retriever_state.get("top_evidence", [])
            final_state = run_critic_agent(query, evidence)
        except Exception as exc:
            raise ServiceUnavailableError(f"Critic Agent failed: {exc}") from exc

        report = final_state["critic_report"]

        return CriticAgentResponse(
            original_query=report["original_query"],
            evidence_count=report["evidence_count"],
            label_counts=report["label_counts"],
            agreement_rate=report["agreement_rate"],
            contradiction_ratio=report["contradiction_ratio"],
            average_quality_score=report["average_quality_score"],
            contradictions=[ContradictionResponse(**c) for c in report["contradictions"]],
            contradiction_method=report["contradiction_method"],
            labeling_method=report["labeling_method"],
            evidence=[
                ScoredEvidenceResponse(
                    chunk_id=e["chunk_id"],
                    doc_id=e["doc_id"],
                    source_title=e["source_title"],
                    text=e["text"],
                    label=e["label"],
                    reasoning=e["reasoning"],
                    score=e["score"],
                    final_rank_score=e["final_rank_score"],
                    specificity_score=e["specificity_score"],
                    source_reliability_score=e["source_reliability_score"],
                    quality_score=e["quality_score"],
                )
                for e in report["evidence"]
            ],
        )


_service_singleton: Optional[CriticAgentService] = None


def get_critic_agent_service() -> CriticAgentService:
    global _service_singleton
    if _service_singleton is None:
        _service_singleton = CriticAgentService()
    return _service_singleton
