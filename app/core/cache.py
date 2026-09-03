"""
DeepTrace — Redis Cache Wrapper
Simple async-friendly wrapper around redis-py for caching and rate limiting.
"""

import json
from typing import Any

import redis.asyncio as aioredis

from app.config import get_settings

settings = get_settings()
_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Return (or create) the shared async Redis connection pool."""
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis


async def cache_set(key: str, value: Any, ttl_seconds: int = 300) -> None:
    """Serialize value to JSON and store in Redis with TTL."""
    r = await get_redis()
    await r.setex(key, ttl_seconds, json.dumps(value))


async def cache_get(key: str) -> Any | None:
    """Retrieve and deserialize a cached value. Returns None on miss."""
    r = await get_redis()
    raw = await r.get(key)
    return json.loads(raw) if raw else None


async def cache_delete(key: str) -> None:
    """Invalidate a cache key."""
    r = await get_redis()
    await r.delete(key)


async def cache_delete_pattern(pattern: str) -> int:
    """Delete all keys matching a pattern. Returns count of deleted keys."""
    r = await get_redis()
    keys = await r.keys(pattern)
    if keys:
        return await r.delete(*keys)
    return 0
