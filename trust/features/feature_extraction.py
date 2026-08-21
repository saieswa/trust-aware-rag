"""
Trust Feature Extraction.

Takes a Critic Agent report (agents/critic/report_builder.py's output) and
extracts five numeric features, each normalized to the 0-1 range, that the
trust formula (trust/formula/trust_formula.py) combines into one score.

All five features are computed only over "support"-labeled evidence where
that makes sense (reliability, similarity) — the whole point of the Critic
Agent's labeling is to separate usable evidence from evidence that's
contradicted by something more reliable, so the trust score should reflect
the quality of what we'd ACTUALLY use to answer, not evidence we're about
to discard.
"""

from __future__ import annotations

from typing import Any, Dict, List

# A single supporting document isn't necessarily untrustworthy, but multiple
# INDEPENDENT documents agreeing is a stronger trust signal than one
# document repeated across several chunks. This constant is where the
# "number of sources" feature saturates at full credit.
SOURCE_COUNT_SATURATION = 3


def _mean(values: List[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def extract_trust_features(critic_report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract the five trust features from a Critic Agent report.

    Equations for each feature are documented here; the *weighting* of
    these features into one final score happens in trust_formula.py —
    kept separate so "what do we measure" and "how much does each thing
    matter" can be reasoned about (and tuned) independently.
    """
    evidence: List[Dict[str, Any]] = critic_report.get("evidence", [])
    total_evidence = len(evidence) or 1  # avoid division by zero

    support_chunks = [e for e in evidence if e["label"] == "support"]
    # Fallback: if nothing was labeled "support" (e.g. all evidence was
    # neutral/contradicted), compute reliability/similarity over the full
    # evidence set instead of an empty list, so the score still reflects
    # *something* about what was retrieved rather than defaulting to zero
    # by convention alone.
    reliability_source = support_chunks or evidence
    similarity_source = support_chunks or evidence

    # ---------- 1. Agreement Score ----------
    # agreement_score = (# chunks labeled "support") / (total evidence chunks)
    #
    # This is already computed by the Critic Agent's report builder as
    # `agreement_rate` — reused here rather than recomputed, so there's a
    # single source of truth for this number.
    agreement_score = critic_report.get("agreement_rate", len(support_chunks) / total_evidence)

    # ---------- 2. Source Reliability ----------
    # source_reliability = mean(source_reliability_score for chunk in reliability_source)
    #
    # Average of the Critic Agent's per-chunk lexical reliability heuristic
    # (agents/critic/quality_scorer.py), restricted to the evidence we'd
    # actually rely on — a reliable-looking chunk that lost to a contradiction
    # already got excluded via `support_chunks`.
    source_reliability = _mean([c["source_reliability_score"] for c in reliability_source])

    # ---------- 3. Similarity Score ----------
    # similarity_score = mean(retrieval_similarity for chunk in similarity_source)
    #
    # Average retrieval similarity (the Retriever Agent's final_rank_score,
    # falling back to the raw FAISS score if rank score isn't present) —
    # how closely the evidence we're relying on actually matches the
    # question semantically, independent of how "authoritative" it looks.
    similarity_score = _mean(
        [c.get("final_rank_score", c.get("score", 0.0)) for c in similarity_source]
    )

    # ---------- 4. Contradiction Score ----------
    # contradiction_score = min(contradiction_pairs / total_evidence_chunks, 1.0)
    #
    # Already computed by the Critic Agent as `contradiction_ratio`; clipped
    # to 1.0 here as a safety bound since, in principle, a small evidence
    # set with many pairwise contradictions could exceed a ratio of 1.
    contradiction_score = min(critic_report.get("contradiction_ratio", 0.0), 1.0)

    # ---------- 5. Number of Sources ----------
    # source_count_score = min(distinct_document_count / SOURCE_COUNT_SATURATION, 1.0)
    #
    # Counts DISTINCT source documents (doc_id), not chunks — three chunks
    # from the same document are one source, not three. Reaching
    # SOURCE_COUNT_SATURATION distinct documents gives full credit; more
    # than that doesn't add further benefit (diminishing returns).
    distinct_doc_ids = {c["doc_id"] for c in reliability_source}
    source_count_score = round(min(len(distinct_doc_ids) / SOURCE_COUNT_SATURATION, 1.0), 4)

    return {
        "agreement_score": round(agreement_score, 4),
        "source_reliability": source_reliability,
        "similarity_score": similarity_score,
        "contradiction_score": round(contradiction_score, 4),
        "source_count_score": source_count_score,
        # Diagnostics carried through for the JSON output / dashboard, not
        # used directly in the formula itself.
        "diagnostics": {
            "evidence_count": len(evidence),
            "support_count": len(support_chunks),
            "distinct_source_count": len(distinct_doc_ids),
            "contradiction_count": len(critic_report.get("contradictions", [])),
        },
    }
