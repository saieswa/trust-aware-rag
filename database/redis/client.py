"""
Redis connection setup.

Mirrors database/postgres/session.py: this module owns the Redis connection
pool and exposes a single shared client, plus a health-check helper. No RAG
caching logic lives here yet — that gets added once the retrieval pipeline
exists.
"""

from __future__ import annotations

import redis.asyncio as redis

from app.core.config import get_settings

settings = get_settings()

# A connection pool is created once and reused across the app — this avoids
# opening a new TCP connection to Redis on every request.
redis_pool: redis.ConnectionPool = redis.ConnectionPool.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    max_connections=20,
)


def get_redis_client() -> redis.Redis:
    """Returns a Redis client backed by the shared connection pool."""
    return redis.Redis(connection_pool=redis_pool)


async def check_redis_connection() -> bool:
    """Used by the /health endpoint to confirm Redis is reachable."""
    client = get_redis_client()
    try:
        return await client.ping()
    except Exception:
        return False
