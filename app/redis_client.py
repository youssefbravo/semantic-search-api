from functools import lru_cache

import redis

from .config import get_settings

settings = get_settings()


@lru_cache
def get_redis() -> redis.Redis:
    # Single shared client (redis-py is thread-safe and pools connections).
    # decode_responses=True so we work with str, not bytes.
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)
