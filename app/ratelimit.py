"""Distributed token-bucket rate limiter backed by Redis.

Why token bucket: it enforces a steady average rate (refill_per_sec) while still
allowing short bursts up to the bucket capacity — friendlier than a fixed window and
without the edge-of-window doubling problem.

Why a Lua script: the read-modify-write of the bucket (refill, then try to spend a
token) must be ATOMIC across all API instances, or two concurrent requests could
both read the same token count and both succeed. Redis runs the whole script
atomically, giving every instance one shared, race-free source of truth.

Fail-open: if Redis is unreachable we allow the request. For a search API,
availability beats strict enforcement during a Redis outage — documented as a
deliberate tradeoff.
"""
import logging
import time
from functools import lru_cache

import redis

from .config import get_settings
from .redis_client import get_redis

logger = logging.getLogger(__name__)
settings = get_settings()

# KEYS[1]=bucket  ARGV: capacity, refill/sec, now(s), requested
# Returns {allowed(0/1), retry_after_seconds(string, to preserve decimals)}
_TOKEN_BUCKET_LUA = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local requested = tonumber(ARGV[4])

local bucket = redis.call('HMGET', key, 'tokens', 'ts')
local tokens = tonumber(bucket[1])
local ts = tonumber(bucket[2])
if tokens == nil then
  tokens = capacity
  ts = now
end

local elapsed = math.max(0, now - ts)
tokens = math.min(capacity, tokens + elapsed * refill)

local allowed = 0
if tokens >= requested then
  allowed = 1
  tokens = tokens - requested
end

redis.call('HSET', key, 'tokens', tokens, 'ts', now)
-- GC idle buckets once they would have fully refilled.
redis.call('PEXPIRE', key, math.ceil(capacity / refill * 1000))

local retry_after = 0
if allowed == 0 then
  retry_after = (requested - tokens) / refill
end
return {allowed, tostring(retry_after)}
"""


@lru_cache
def _script():
    return get_redis().register_script(_TOKEN_BUCKET_LUA)


def check_rate_limit(identifier: str) -> tuple[bool, float]:
    """Return (allowed, retry_after_seconds). Fails open on Redis errors."""
    if not settings.rate_limit_enabled:
        return True, 0.0
    try:
        allowed, retry_after = _script()(
            keys=[f"ratelimit:{identifier}"],
            args=[
                settings.rate_limit_capacity,
                settings.rate_limit_refill_per_sec,
                time.time(),
                1,
            ],
        )
        return bool(int(allowed)), float(retry_after)
    except redis.RedisError:
        logger.warning("Rate limiter unavailable; failing open", exc_info=True)
        return True, 0.0
