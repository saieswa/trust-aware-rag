"""
PostgreSQL connection setup using async SQLAlchemy.

This module owns exactly three things:
1. `engine`       — the connection pool to PostgreSQL.
2. `AsyncSessionLocal` — a factory that creates new database sessions.
3. `Base`         — the declarative base every ORM model (added in a later
                     step, under database/postgres/models/) will inherit from.

Nothing here talks to FastAPI directly — `backend/app/api/dependencies/database.py`
wraps `AsyncSessionLocal` into a FastAPI dependency that routes can use.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_DEBUG,       # log SQL statements in debug mode only
    pool_pre_ping=True,            # detect and discard dead connections automatically
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models in database/postgres/models/."""

    pass


@asynccontextmanager
async def get_session_context() -> AsyncIterator[AsyncSession]:
    """
    Context-manager form of a session, for use outside of FastAPI request
    handling (e.g. in scripts, background jobs, or the agent pipeline).
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def check_database_connection() -> bool:
    """Used by the /health endpoint to confirm PostgreSQL is reachable."""
    from sqlalchemy import text

    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
