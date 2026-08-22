"""
Trust Feature Extraction.

Extracts five normalized numeric features from a Critic Agent report.
If no supporting evidence was verified by the Critic, reliability and
similarity features drop to zero, forcing an honest abstention.
"""

from __future__ import annotations

from typing import Any, Dict, List

SOURCE_COUNT_SATURATION = 3


def _mean(values: List[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def extract_trust_features(critic_report: Dict[str, Any]) -> Dict[str, Any]:
    evidence: List[Dict[str, Any]] = critic_report.get("evidence", [])
    total_evidence = len(evidence) or 1

    support_chunks = [e for e in evidence if e.get("label") == "support"]

    # If zero chunks support the claim, features reflect lack of support
    if not support_chunks:
        distinct_doc_ids = {c["doc_id"] for c in evidence}
        return {
            "agreement_score": 0.0,
            "source_reliability": 0.0,
            "similarity_score": 0.0,
            "contradiction_score": min(critic_report.get("contradiction_ratio", 0.0), 1.0),
            "source_count_score": 0.0,
            "diagnostics": {
                "evidence_count": len(evidence),
                "support_count": 0,
                "distinct_source_count": len(distinct_doc_ids),
                "contradiction_count": len(critic_report.get("contradictions", [])),
            },
        }

    # 1. Agreement Score
    agreement_score = len(support_chunks) / total_evidence

    # 2. Source Reliability over verified supporting chunks
    source_reliability = _mean([c.get("source_reliability_score", 0.5) for c in support_chunks])

    # 3. Similarity Score over verified supporting chunks
    similarity_score = _mean(
        [c.get("final_rank_score", c.get("score", 0.0)) for c in support_chunks]
    )

    # 4. Contradiction Score
    contradiction_score = min(critic_report.get("contradiction_ratio", 0.0), 1.0)

    # 5. Number of Sources
    distinct_doc_ids = {c["doc_id"] for c in support_chunks}
    source_count_score = round(min(len(distinct_doc_ids) / SOURCE_COUNT_SATURATION, 1.0), 4)

    return {
        "agreement_score": round(agreement_score, 4),
        "source_reliability": source_reliability,
        "similarity_score": similarity_score,
        "contradiction_score": round(contradiction_score, 4),
        "source_count_score": source_count_score,
        "diagnostics": {
            "evidence_count": len(evidence),
            "support_count": len(support_chunks),
            "distinct_source_count": len(distinct_doc_ids),
            "contradiction_count": len(critic_report.get("contradictions", [])),
        },
    }
