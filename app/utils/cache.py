"""Redis-backed caching helpers for content endpoints."""
from __future__ import annotations

import json
import logging
from typing import Any, Optional, TYPE_CHECKING

from fastapi.encoders import jsonable_encoder

from app.config import settings

try:  # pragma: no cover - optional dependency guard
    import redis.asyncio as redis
except ImportError:  # pragma: no cover
    redis = None  # type: ignore

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 300
_redis_client: Optional["Redis"] = None


def _is_cache_enabled() -> bool:
    return bool(settings.CACHE_ENABLED and settings.REDIS_URL and redis is not None)


def get_redis_client() -> Optional["Redis"]:
    """Return a singleton Redis client when caching is enabled."""
    global _redis_client  # pylint: disable=global-statement

    if not _is_cache_enabled():
        return None

    if _redis_client is None:
        try:
            _redis_client = redis.from_url(  # type: ignore[union-attr]
                settings.REDIS_URL, decode_responses=True
            )
        except Exception as exc:  # pragma: no cover - connection issues
            logger.error("Unable to initialize Redis client: %s", exc)
            _redis_client = None
    return _redis_client


async def get_cache_value(key: str) -> Optional[Any]:
    client = get_redis_client()
    if not client:
        return None
    cached = await client.get(key)
    if not cached:
        return None
    try:
        return json.loads(cached)
    except json.JSONDecodeError:
        logger.warning("Cache entry for key %s is not valid JSON", key)
        return None


async def set_cache_value(key: str, value: Any, ttl: int = _CACHE_TTL_SECONDS) -> None:
    client = get_redis_client()
    if not client:
        return
    payload = json.dumps(jsonable_encoder(value))
    await client.set(key, payload, ex=ttl)


async def invalidate_user_cache(user_id: str, content_id: Optional[int] = None) -> None:
    client = get_redis_client()
    if not client:
        return
    keys = [f"user:{user_id}:contents"]
    if content_id is not None:
        keys.append(f"user:{user_id}:content:{content_id}")
    await client.delete(*keys)