"""
TrustScoreLog — persisted record of one trust score computation.

Every call to the trust scoring API writes one row here (see
backend/app/services/trust_service.py). This is what the Trust Dashboard
API aggregates over: average trust score, how often the system abstains,
how often contradictions show up, etc. — the same statistics the
project's design docs describe for a "Trust Dashboard" page.
"""

from __future__ import annotations

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.postgres.models.base import TimestampMixin
from database.postgres.session import Base


class TrustScoreLog(Base, TimestampMixin):
    __tablename__ = "trust_score_logs"

    query: Mapped[str] = mapped_column(Text, nullable=False)
    trust_score: Mapped[float] = mapped_column(Float, nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)  # answer | retrieve_more | abstain
    scoring_method: Mapped[str] = mapped_column(String(20), nullable=False, default="formula")  # formula | ml

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
        return f"<TrustScoreLog id={self.id} score={self.trust_score} decision={self.decision!r}>"
