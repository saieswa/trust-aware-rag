"""
Trust Engine — Orchestration and JSON Output.

Ties together the Critic Agent (previous step), feature extraction, and a
trust SCORER — either the hand-built formula or the trained XGBoost model
— into one function producing the final structured trust report.

This is intentionally a plain function, not a LangGraph graph: unlike the
Retriever/Critic agents, there's no branching or multi-step reasoning
here — it's a straight-line composition of already-built pieces.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from loguru import logger

from agents.critic.agent import run_critic_agent
from agents.retriever.agent import run_retriever_agent
from trust.features.feature_extraction import extract_trust_features
from trust.formula.trust_formula import compute_trust_score
from trust.model.trust_model import get_trust_ml_model

ScoringMethod = str  # "formula" | "ml" | "auto"


def _score(features: Dict[str, Any], method: ScoringMethod) -> Dict[str, Any]:
    """
    Dispatches to the formula or the trained ML model, following the same
    graceful-degradation pattern as every LLM call elsewhere in this
    project: `method="ml"` prefers the trained XGBoost model but falls
    back to the formula if no model has been trained yet, rather than
    erroring. `method="formula"` always uses the hand-built formula.
    `method="auto"` (the default) uses the ML model if one is available,
    the formula otherwise — this is what makes training a new model a
    true drop-in upgrade with zero call-site changes anywhere else.
    """
    if method in ("ml", "auto"):
        ml_model = get_trust_ml_model()
        if ml_model is not None:
            result = ml_model.predict(features)
            return {
                "trust_score": result["trust_score"],
                "decision": result["decision"],
                "scoring_method": "ml",
                "feature_breakdown": result["feature_contributions"],
                "model_trained_at": result["model_trained_at"],
            }
        if method == "ml":
            logger.warning("Trust scoring method 'ml' requested but no trained model exists — falling back to formula.")

    formula_result = compute_trust_score(features)
    return {
        "trust_score": formula_result["trust_score"],
        "decision": formula_result["decision"],
        "scoring_method": "formula",
        "feature_breakdown": formula_result["feature_breakdown"],
        "model_trained_at": None,
    }


def compute_trust_report(
    query: str,
    k: int = 5,
    evidence: Optional[List[Dict[str, Any]]] = None,
    critic_report: Optional[Dict[str, Any]] = None,
    method: ScoringMethod = "auto",
) -> Dict[str, Any]:
    """
    Produces the final trust report JSON for a query.

    Three ways to call this, in increasing order of "work already done":
      - Only `query` given          -> runs Retriever Agent, then Critic Agent.
      - `evidence` given            -> skips Retriever Agent, runs Critic Agent on it.
      - `critic_report` given       -> skips both agents, scores trust directly.

    `method` controls which trust SCORER is used ("formula", "ml", or
    "auto" — see `_score()` above) independently of how the evidence was
    obtained.
    """
    if critic_report is None:
        if evidence is None:
            retriever_state = run_retriever_agent(query, k=k)
            evidence = retriever_state.get("top_evidence", [])
        critic_state = run_critic_agent(query, evidence)
        critic_report = critic_state["critic_report"]

    features = extract_trust_features(critic_report)
    trust_result = _score(features, method)

    report = {
        "query": query,
        "trust_score": trust_result["trust_score"],
        "decision": trust_result["decision"],
        "scoring_method": trust_result["scoring_method"],
        "feature_breakdown": trust_result["feature_breakdown"],
        # Raw feature VALUES, always present regardless of which scorer
        # ran — the formula's breakdown happens to also carry these, but
        # the ML model's SHAP breakdown does not, so this is what
        # persistence (backend/app/services/trust_service.py) should
        # always read from, rather than digging through a breakdown shape
        # that varies by method.
        "raw_features": {k: v for k, v in features.items() if k != "diagnostics"},
        "diagnostics": features["diagnostics"],
        "contradictions": critic_report.get("contradictions", []),
        "contradiction_method": critic_report.get("contradiction_method", "none"),
        "labeling_method": critic_report.get("labeling_method", "none"),
        "evidence": critic_report.get("evidence", []),
    }

    logger.info(
        f"Trust report computed — score={report['trust_score']} decision={report['decision']} "
        f"method={report['scoring_method']} for query: {query!r}"
    )
    return report
