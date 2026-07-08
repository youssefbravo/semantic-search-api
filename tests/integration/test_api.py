"""Integration tests against the FastAPI app.

Marked `integration`: they construct the real app (which loads the models) and need
Postgres reachable. The module skips entirely if either is unavailable, so CI/local
runs without the stack don't fail — they just don't run these.

The Celery worker is NOT required: we monkeypatch the task's .delay so the upload
endpoint enqueues a no-op. This isolates the HTTP/DB behaviour from the worker.
"""
import pytest

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def client():
    pytest.importorskip("sentence_transformers")
    from sqlalchemy import text

    from app.db import engine
    from app.redis_client import get_redis

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        get_redis().ping()
    except Exception:  # noqa: BLE001
        pytest.skip("Postgres/Redis not reachable")

    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["checks"] == {"postgres": True, "redis": True}


def test_metrics_endpoint_is_exposed(client):
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "http_requests_total" in r.text


def test_upload_returns_202_without_worker(client, monkeypatch):
    import app.routers.documents as documents

    captured = {}
    monkeypatch.setattr(
        documents.ingest_document,
        "delay",
        lambda *args, **kwargs: captured.setdefault("args", args),
    )

    r = client.post(
        "/documents",
        files={"file": ("note.txt", b"Hello world. This is a test document.", "text/plain")},
    )
    assert r.status_code == 202
    body = r.json()
    assert body["status"] == "pending"
    assert "args" in captured  # task was enqueued

    status = client.get(f"/documents/{body['id']}")
    assert status.status_code == 200
    assert status.json()["status"] == "pending"


def test_upload_requires_api_key_when_configured(client, monkeypatch):
    import app.routers.documents as documents

    monkeypatch.setattr(documents.settings, "ingest_api_key", "secret-key")
    monkeypatch.setattr(documents.ingest_document, "delay", lambda *a, **k: None)

    no_key = client.post(
        "/documents",
        files={"file": ("note.txt", b"Hello world.", "text/plain")},
    )
    assert no_key.status_code == 401

    bad_key = client.post(
        "/documents",
        files={"file": ("note.txt", b"Hello world.", "text/plain")},
        headers={"X-API-Key": "wrong"},
    )
    assert bad_key.status_code == 401

    good_key = client.post(
        "/documents",
        files={"file": ("note.txt", b"Hello world.", "text/plain")},
        headers={"X-API-Key": "secret-key"},
    )
    assert good_key.status_code == 202


def test_empty_query_is_rejected(client):
    r = client.post("/search", json={"query": "", "mode": "semantic", "k": 5})
    assert r.status_code == 422  # pydantic min_length=1


def test_unknown_document_is_404(client):
    r = client.get("/documents/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404
