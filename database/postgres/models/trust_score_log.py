"""
TrustScoreLog — persisted record of one trust score computation.

Every call to the trust scoring or evaluation API writes one row here.
Preserves query, document association (doc_id, document_name), trust score,
decision, feature breakdown, and timestamps.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.postgres.models.base import TimestampMixin
from database.postgres.session import Base


class TrustScoreLog(Base, TimestampMixin):
    __tablename__ = "trust_score_logs"

    query: Mapped[str] = mapped_column(Text, nullable=False)
    doc_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    document_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    trust_score: Mapped[float] = mapped_column(Float, nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)  # answer | retrieve_more | abstain
    scoring_method: Mapped[str] = mapped_column(String(20), nullable=False, default="formula")  # formula | ml
    final_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ---------- Feature values (post-extraction, pre-weighting) ----------
    agreement_score: Mapped[float] = mapped_column(Float, nullable=False)
    source_reliability: Mapped[float] = mapped_column(Float, nullable=False)
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    contradiction_score: Mapped[float] = mapped_column(Float, nullable=False)
    source_count_score: Mapped[float] = mapped_column(Float, nullable=False)

    # ---------- Diagnostics ----------
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    support_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    distinct_source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    contradiction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    contradiction_method: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    labeling_method: Mapped[str] = mapped_column(String(20), nullable=False, default="none")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<TrustScoreLog id={self.id} doc={self.doc_id!r} score={self.trust_score} decision={self.decision!r}>"
