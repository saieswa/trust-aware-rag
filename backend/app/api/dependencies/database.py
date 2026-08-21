"""
FastAPI dependency for database access.

Any route that needs the database declares:

    from app.api.dependencies.database import get_db

    @router.get("/something")
    async def handler(db: AsyncSession = Depends(get_db)):
        ...

FastAPI calls `get_db()` per-request, hands the route a session, and this
generator's `finally` block guarantees the session is always closed —
even if the route raises an exception.
"""

from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from database.postgres.session import AsyncSessionLocal


async def get_db() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
