"""Redis-backed cache for repeated search queries.

Key = hash(query + mode + k): two genuinely identical searches hit the cache, a
change in any parameter misses. Entries carry a TTL so results can't outlive newly
ingested documents by more than cache_ttl_seconds. All operations degrade gracefully
(treat Redis errors as a cache miss) so a Redis hiccup never fails a search.
"""
import hashlib
import json
import logging

import redis

from .config import get_settings
from .redis_client import get_redis

logger = logging.getLogger(__name__)
settings = get_settings()


def cache_key(query: str, mode: str, k: int) -> str:
    raw = f"{mode}|{k}|{query.strip().lower()}"
    return "search:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_cached(key: str) -> dict | None:
    if not settings.cache_enabled:
        return None
    try:
        val = get_redis().get(key)
    except redis.RedisError:
        logger.warning("Cache read failed; treating as miss", exc_info=True)
        return None
    return json.loads(val) if val else None


def set_cached(key: str, payload: dict) -> None:
    if not settings.cache_enabled:
        return
    try:
        get_redis().setex(key, settings.cache_ttl_seconds, json.dumps(payload))
    except redis.RedisError:
        logger.warning("Cache write failed; skipping", exc_info=True)
