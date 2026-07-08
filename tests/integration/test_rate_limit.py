"""Rate-limiter tests (audit plan §1.1 'rate limiter is atomic' + §1.3 clean 429).

Two levels:
 1. Atomicity of the Redis Lua token bucket under real concurrency: fire N threads at
    a fresh bucket and prove the limiter never admits more than capacity (+ whatever
    trickle refilled during the burst). If the read-modify-write were not atomic, two
    threads would read the same token count and BOTH spend it, admitting > capacity.
 2. End-to-end: hammering /search past the burst returns a clean 429 with Retry-After.

Marked `integration`: needs Redis (and, for the HTTP test, the app + Postgres).
"""
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def redis_ok():
    pytest.importorskip("redis")
    from app.redis_client import get_redis

    try:
        get_redis().ping()
    except Exception:  # noqa: BLE001
        pytest.skip("Redis not reachable")
    return True


def test_token_bucket_is_atomic_under_concurrency(redis_ok):
    from app.config import get_settings
    from app.ratelimit import check_rate_limit

    settings = get_settings()
    cap = settings.rate_limit_capacity
    refill = settings.rate_limit_refill_per_sec

    # A brand-new identifier => a full, uncontended bucket of exactly `cap` tokens.
    ident = f"attest-{uuid.uuid4()}"
    n = cap * 4  # oversubscribe 4x

    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=n) as pool:
        results = list(pool.map(lambda _: check_rate_limit(ident)[0], range(n)))
    elapsed = time.perf_counter() - start

    allowed = sum(1 for ok in results if ok)
    # Upper bound: initial capacity + tokens that legitimately refilled mid-burst.
    theoretical_max = cap + int(elapsed * refill) + 1

    assert allowed >= cap, f"expected at least the full bucket ({cap}) to pass, got {allowed}"
    assert allowed <= theoretical_max, (
        f"admitted {allowed} > atomic max {theoretical_max} "
        f"(cap={cap}, elapsed={elapsed:.3f}s) -> token double-spend / non-atomic"
    )
    assert allowed < n, "limiter did not limit at all"


def test_disabled_limiter_allows_everything(redis_ok, monkeypatch):
    import app.ratelimit as rl

    monkeypatch.setattr(rl.settings, "rate_limit_enabled", False)
    ident = f"attest-off-{uuid.uuid4()}"
    assert all(check_ok(rl, ident) for _ in range(100))


def check_ok(rl, ident):
    return rl.check_rate_limit(ident)[0]


def test_http_search_returns_clean_429_with_retry_after():
    pytest.importorskip("sentence_transformers")
    from sqlalchemy import text

    from app.db import engine

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        pytest.skip("Postgres not reachable")

    from fastapi.testclient import TestClient

    from app.config import get_settings
    from app.main import app

    cap = get_settings().rate_limit_capacity
    client = TestClient(app)

    # Fire well past the burst capacity as fast as possible for one client identity.
    statuses = []
    for _ in range(cap + 15):
        r = client.post("/search", json={"query": "load", "mode": "keyword", "k": 3})
        statuses.append(r)

    limited = [r for r in statuses if r.status_code == 429]
    assert limited, "expected at least one 429 after exceeding the burst"
    for r in limited:
        assert r.status_code != 500
        assert "Retry-After" in r.headers, "429 must carry a Retry-After header"
        assert int(r.headers["Retry-After"]) >= 0
