"""
Shared ORM mixin for common columns.

Every real table added in later steps (e.g. `queries`, `evidence_chunks`,
`trust_scores`) will inherit both `Base` (database/postgres/session.py) and
this `TimestampMixin`, so we don't repeat `id`/`created_at`/`updated_at` on
every model. No actual domain tables are defined yet — this file exists so
Alembic has something real to anchor its first migration against, and so
the pattern is established before RAG-specific models are added.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
