"""
Document-Scoped Redis Caching and Active Document Management.

Ensures all cached retrieval results, trust scores, and synthesized answers
are strictly scoped by `document_id`. Prevents cache contamination between
different research papers and documents.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional

from loguru import logger

from database.redis.client import get_redis_client

# In-memory fallback if Redis connection is temporarily offline
_memory_active_doc_id: Optional[str] = None
_memory_cache: Dict[str, Any] = {}

ACTIVE_DOC_KEY_PREFIX = "trag:active_doc"
CACHE_TTL_SECONDS = 3600  # 1 hour


def _compute_query_hash(query: str) -> str:
    normalized = " ".join(query.strip().lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


class CacheService:
    def __init__(self):
        self._redis = get_redis_client()

    async def get_active_document_id(self, session_id: Optional[str] = None) -> Optional[str]:
        """Returns the currently active document ID."""
        global _memory_active_doc_id
        key = f"{ACTIVE_DOC_KEY_PREFIX}:{session_id}" if session_id else f"{ACTIVE_DOC_KEY_PREFIX}:global"
        try:
            val = await self._redis.get(key)
            if val:
                return val.decode("utf-8") if isinstance(val, bytes) else str(val)
        except Exception as exc:
            logger.warning(f"Redis get_active_document_id error ({exc}); using in-memory state.")
        return _memory_active_doc_id

    async def set_active_document_id(self, doc_id: str, session_id: Optional[str] = None) -> None:
        """Sets the active document ID."""
        global _memory_active_doc_id
        _memory_active_doc_id = doc_id
        key = f"{ACTIVE_DOC_KEY_PREFIX}:{session_id}" if session_id else f"{ACTIVE_DOC_KEY_PREFIX}:global"
        try:
            await self._redis.set(key, doc_id, ex=86400 * 7)  # 7 days
            logger.info(f"[CACHE] Active document set to doc_id={doc_id!r} (key={key}).")
        except Exception as exc:
            logger.warning(f"Redis set_active_document_id error ({exc}); set in-memory only.")

    async def get_cached(self, scope: str, doc_id: str, query: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a document-scoped cache entry.
        Key pattern: trag:cache:{scope}:{doc_id}:{query_hash}
        """
        q_hash = _compute_query_hash(query)
        cache_key = f"trag:cache:{scope}:{doc_id}:{q_hash}"
        try:
            data = await self._redis.get(cache_key)
            if data:
                logger.info(f"[CACHE HIT] scope={scope} doc_id={doc_id} query={query!r}")
                return json.loads(data)
        except Exception as exc:
            logger.warning(f"Redis get_cached error ({exc}); checking in-memory.")

        return _memory_cache.get(cache_key)

    async def set_cached(self, scope: str, doc_id: str, query: str, data: Dict[str, Any]) -> None:
        """
        Stores a document-scoped cache entry.
        """
        q_hash = _compute_query_hash(query)
        cache_key = f"trag:cache:{scope}:{doc_id}:{q_hash}"
        _memory_cache[cache_key] = data
        try:
            await self._redis.set(cache_key, json.dumps(data), ex=CACHE_TTL_SECONDS)
            logger.info(f"[CACHE SET] key={cache_key}")
        except Exception as exc:
            logger.warning(f"Redis set_cached error ({exc}); cached in-memory only.")

    async def invalidate_document_cache(self, doc_id: str) -> None:
        """Invalidates all cached results for a specific document ID."""
        try:
            pattern = f"trag:cache:*:{doc_id}:*"
            keys = []
            async for k in self._redis.scan_iter(match=pattern):
                keys.append(k)
            if keys:
                await self._redis.delete(*keys)
                logger.info(f"[CACHE INVALIDATE] Deleted {len(keys)} keys for doc_id={doc_id!r}.")
        except Exception as exc:
            logger.warning(f"Redis cache invalidation error ({exc}).")

        # Invalidate in-memory
        to_del = [k for k in _memory_cache if f":{doc_id}:" in k]
        for k in to_del:
            _memory_cache.pop(k, None)


_cache_service = CacheService()


def get_cache_service() -> CacheService:
    return _cache_service
