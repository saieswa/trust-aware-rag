"""
FastAPI dependency for Redis access.

Usage in a route:

    from app.api.dependencies.redis import get_redis

    @router.get("/something")
    async def handler(cache = Depends(get_redis)):
        await cache.get("some_key")
"""

import redis.asyncio as redis

from database.redis.client import get_redis_client


async def get_redis() -> redis.Redis:
    return get_redis_client()
