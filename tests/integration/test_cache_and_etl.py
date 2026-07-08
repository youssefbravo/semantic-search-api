"""Cache correctness (audit plan 'cache actually caches') and ETL failure behavior
('ETL survives failure -> ... -> index consistent').

Marked `integration`: needs Redis + Postgres (+ models for the HTTP cache test).
"""
import uuid

import pytest

pytestmark = pytest.mark.integration


# ===========================================================================
# Cache
# ===========================================================================
@pytest.fixture(scope="module")
def redis_ok():
    pytest.importorskip("redis")
    from app.redis_client import get_redis

    try:
        get_redis().ping()
    except Exception:  # noqa: BLE001
        pytest.skip("Redis not reachable")
    return True


def test_cache_set_then_get_roundtrips_with_ttl(redis_ok):
    from app.cache import cache_key, get_cached, set_cached
    from app.config import get_settings
    from app.redis_client import get_redis

    key = cache_key(f"unit cache probe {uuid.uuid4()}", "hybrid", 5)
    payload = {"count": 1, "results": [{"x": 1}]}

    assert get_cached(key) is None  # cold miss
    set_cached(key, payload)
    assert get_cached(key) == payload  # warm hit

    # TTL is actually applied (bounds staleness) — not a long-lived key.
    ttl = get_redis().ttl(key)
    assert 0 < ttl <= get_settings().cache_ttl_seconds


def test_cache_key_normalizes_edge_whitespace_and_case(redis_ok):
    from app.cache import cache_key

    # cache_key does query.strip().lower(): leading/trailing whitespace + case are
    # normalized (so trivially-different repeats still hit), internal spacing is NOT.
    assert cache_key("  Hello World ", "semantic", 5) == cache_key(
        "hello world", "semantic", 5
    )
    # Internal whitespace is significant (documents the actual contract).
    assert cache_key("hello  world", "semantic", 5) != cache_key(
        "hello world", "semantic", 5
    )


def test_http_identical_search_is_served_from_cache(redis_ok):
    pytest.importorskip("sentence_transformers")
    from sqlalchemy import text

    from app.db import engine

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        pytest.skip("Postgres not reachable")

    import app.ratelimit as rl
    from fastapi.testclient import TestClient

    from app.main import app

    # Isolate from the shared per-client bucket used by other TestClient tests.
    prev = rl.settings.rate_limit_enabled
    rl.settings.rate_limit_enabled = False
    try:
        client = TestClient(app)
        body = {"query": f"cache path probe {uuid.uuid4()}", "mode": "keyword", "k": 3}

        first = client.post("/search", json=body).json()
        second = client.post("/search", json=body).json()

        assert first["cached"] is False
        assert second["cached"] is True
        # Same answer served from cache.
        assert first["count"] == second["count"]
        assert [h["chunk_id"] for h in first["results"]] == [
            h["chunk_id"] for h in second["results"]
        ]
        # Cache hit is dramatically cheaper (no embed/retrieve).
        assert second["latency_ms"] <= first["latency_ms"]
    finally:
        rl.settings.rate_limit_enabled = prev


# ===========================================================================
# ETL failure behavior
# ===========================================================================
def _fresh_doc():
    from app.db import SessionLocal
    from app.models import DocStatus, Document

    db = SessionLocal()
    doc = Document(filename="boom.txt", content_type="text/plain", status=DocStatus.pending)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    doc_id = doc.id
    db.close()
    return doc_id


def test_ingestion_failure_marks_failed_and_leaves_no_partial_chunks(tmp_path, monkeypatch):
    """A parse/embed failure must: re-raise, set status=failed with the error, and
    leave ZERO chunks for the doc (atomic commit => the index stays consistent)."""
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import Chunk, DocStatus, Document
    import app.tasks as tasks

    try:
        from app.db import engine

        with engine.connect() as conn:
            conn.execute(select(1))
    except Exception:  # noqa: BLE001
        pytest.skip("Postgres not reachable")

    doc_id = _fresh_doc()
    raw = tmp_path / f"{doc_id}.txt"
    raw.write_bytes(b"whatever")

    # Force the pipeline to blow up mid-task.
    monkeypatch.setattr(tasks, "extract_text", lambda *a, **k: (_ for _ in ()).throw(ValueError("boom")))

    with pytest.raises(ValueError, match="boom"):
        tasks.ingest_document.run(str(doc_id), str(raw))

    db = SessionLocal()
    try:
        doc = db.get(Document, doc_id)
        assert doc.status == DocStatus.failed
        assert "boom" in (doc.error or "")
        n_chunks = db.execute(
            select(Chunk).where(Chunk.document_id == doc_id)
        ).all()
        assert n_chunks == [], "failed ingestion left orphan chunks -> inconsistent index"
    finally:
        # cleanup
        doc = db.get(Document, doc_id)
        if doc:
            db.delete(doc)
            db.commit()
        db.close()


def test_retry_is_NOT_actually_configured():
    """DOCUMENTS A REAL GAP (see AUDIT.md C7): the task sets max_retries=2 but never
    calls self.retry() and configures no autoretry_for, so an unhandled exception does
    NOT retry — it fails immediately. This test pins that reality so the README claim
    can be corrected (or the code fixed to make the claim true)."""
    import app.tasks as tasks

    # No declarative autoretry.
    assert getattr(tasks.ingest_document, "autoretry_for", ()) in ((), None)
    # And the source performs a bare re-raise, not self.retry(...).
    import inspect

    src = inspect.getsource(tasks.ingest_document)
    assert "self.retry" not in src, "if this fires, retries were wired — update the claim to TRUE"
