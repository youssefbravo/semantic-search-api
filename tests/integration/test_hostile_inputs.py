"""Hostile-input hardening suite (audit plan §1.3).

Feed the API garbage on purpose. The contract: **every** case returns a clean 4xx
(or a valid 2xx) with a helpful message — never an unhandled 500. The overarching
assertion in every test is `status_code != 500`; specific expected codes are asserted
where the behavior is well-defined.

Marked `integration`: needs the app (models) + Postgres. Skips cleanly otherwise.
"""
import pytest

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def client():
    pytest.importorskip("sentence_transformers")
    from sqlalchemy import text

    from app.db import engine

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        pytest.skip("Postgres not reachable")

    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


# ---------------------------------------------------------------------------
# Search: malformed / out-of-range request bodies -> 422 (never 500)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "body, why",
    [
        ({"query": "", "mode": "semantic", "k": 5}, "empty query (min_length=1)"),
        ({"query": "x" * 10000, "mode": "semantic", "k": 5}, "10k-char query (max_length=1000)"),
        ({"query": "ok", "mode": "semantic", "k": 0}, "k=0 (ge=1)"),
        ({"query": "ok", "mode": "semantic", "k": -5}, "k=-5 (ge=1)"),
        ({"query": "ok", "mode": "semantic", "k": 100000}, "k=100000 (le=50)"),
        ({"query": "ok", "mode": "not_a_mode", "k": 5}, "invalid enum mode"),
        ({"mode": "semantic", "k": 5}, "missing required query field"),
    ],
)
def test_search_invalid_body_returns_422(client, body, why):
    r = client.post("/search", json=body)
    assert r.status_code == 422, f"{why}: got {r.status_code} / {r.text[:200]}"


def test_search_malformed_json_returns_422(client):
    r = client.post(
        "/search",
        content=b"{ this is not : valid json ",
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 422
    assert r.status_code != 500


def test_search_wrong_content_type_is_not_500(client):
    # Send the body as form data instead of JSON.
    r = client.post("/search", data={"query": "hello", "mode": "semantic", "k": "5"})
    assert r.status_code != 500
    assert 400 <= r.status_code < 500


# ---------------------------------------------------------------------------
# Search: exotic-but-valid query strings -> clean 200, never 500
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "query, mode, why",
    [
        ("🚀🔥😀 vector search 日本語 مرحبا", "semantic", "emoji + CJK + RTL"),
        ("'; DROP TABLE chunks; --", "keyword", "SQL-injection-ish (BM25 path)"),
        ("'; DROP TABLE chunks; --", "semantic", "SQL-injection-ish (vector path)"),
        ("<script>alert(1)</script>", "hybrid", "HTML/script tags"),
        ("+-&|!(){}[]^\"~*?:\\/", "keyword", "all BM25 special chars -> sanitized empty"),
        ("a", "hybrid", "single char"),
        ("café résumé naïve", "semantic", "accented latin"),
    ],
)
def test_search_exotic_queries_return_clean_200(client, query, mode, why):
    r = client.post("/search", json={"query": query, "mode": mode, "k": 5})
    assert r.status_code == 200, f"{why}: {r.status_code} / {r.text[:200]}"
    body = r.json()
    assert "results" in body and isinstance(body["results"], list)


def test_bm25_only_punctuation_query_returns_empty_not_error(client):
    # Sanitizes to empty -> keyword_search returns [] -> clean 200 with 0 results.
    r = client.post("/search", json={"query": ")))((( ***", "mode": "keyword", "k": 5})
    assert r.status_code == 200
    assert r.json()["count"] == 0


# ---------------------------------------------------------------------------
# Upload: hostile files -> clean 4xx synchronously, or 202 (async, worker handles)
# ---------------------------------------------------------------------------
def test_upload_zero_byte_file_is_400(client):
    r = client.post("/documents", files={"file": ("empty.pdf", b"", "application/pdf")})
    assert r.status_code == 400
    assert "empty" in r.text.lower()


def test_upload_oversized_file_is_413(client):
    # 26 MB > the 25 MB cap in config. Must reject before doing any work.
    big = b"x" * (26 * 1024 * 1024)
    r = client.post("/documents", files={"file": ("big.pdf", big, "application/pdf")})
    assert r.status_code == 413


def test_upload_exe_renamed_to_pdf_is_not_500(client, monkeypatch):
    # A .exe masquerading as .pdf: the API accepts (202) and the worker will mark it
    # failed on parse. The API itself must not 500. We monkeypatch .delay so no real
    # worker/enqueue is needed.
    import app.routers.documents as documents

    monkeypatch.setattr(documents.ingest_document, "delay", lambda *a, **k: None)
    fake_exe = b"MZ\x90\x00\x03" + b"\x00" * 200  # PE header magic
    r = client.post("/documents", files={"file": ("malware.pdf", fake_exe, "application/pdf")})
    assert r.status_code == 202
    assert r.status_code != 500


def test_upload_corrupt_pdf_is_not_500(client, monkeypatch):
    import app.routers.documents as documents

    monkeypatch.setattr(documents.ingest_document, "delay", lambda *a, **k: None)
    corrupt = b"%PDF-1.4 broken garbage not really a pdf"
    r = client.post("/documents", files={"file": ("corrupt.pdf", corrupt, "application/pdf")})
    assert r.status_code == 202
