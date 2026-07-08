"""Functional mode tests against the ingested eval corpus (audit plan C2/C3):

  C2 keyword (BM25) works  — an exact rare term retrieves the chunk that contains it.
  C3 semantic works        — a paraphrase with no lexical overlap finds a chunk that
                             BM25 misses entirely.

Marked `integration`: needs the app (models) + Postgres WITH the eval corpus ingested
(`python -m eval.ingest_corpus --reset`). Skips cleanly if the stack/corpus isn't there.
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
            n = conn.execute(text("SELECT count(*) FROM chunks")).scalar()
    except Exception:  # noqa: BLE001
        pytest.skip("Postgres/chunks not reachable")
    if not n:
        pytest.skip("corpus not ingested (run eval.ingest_corpus --reset)")

    import app.ratelimit as rl
    from fastapi.testclient import TestClient

    from app.main import app

    prev = rl.settings.rate_limit_enabled
    rl.settings.rate_limit_enabled = False  # isolate from the shared per-client bucket
    yield TestClient(app)
    rl.settings.rate_limit_enabled = prev


def _search(client, query, mode, k=3):
    r = client.post("/search", json={"query": query, "mode": mode, "k": k})
    assert r.status_code == 200, r.text
    return r.json()["results"]


def test_c2_keyword_exact_term_finds_its_chunk(client):
    # 'ef_search' is a rare exact token that appears only in the HNSW/ANN passage.
    hits = _search(client, "ef_search", "keyword", k=3)
    assert hits, "keyword search returned nothing for an in-corpus exact term"
    assert "ef_search" in hits[0]["content"], "top BM25 hit does not contain the exact term"


def test_c3_semantic_finds_paraphrase_that_bm25_misses(client):
    # Paraphrase of 'concurrent editing / transactions', deliberately sharing NO
    # content words with the target passage (which talks about ACID/transactions/
    # isolation). Semantic should surface it; BM25 has nothing to match on.
    query = "how many people can edit data at the same time safely"

    semantic = _search(client, query, "semantic", k=3)
    keyword = _search(client, query, "keyword", k=3)

    def mentions_transactions(h):
        c = h["content"].lower()
        return "acid" in c or "transaction" in c or "isolation" in c

    assert any(mentions_transactions(h) for h in semantic), (
        "semantic failed to surface the transactions/ACID passage for a clear paraphrase"
    )
    assert not any(mentions_transactions(h) for h in keyword), (
        "BM25 unexpectedly matched the target — pick a query with less lexical overlap"
    )


def test_hybrid_and_rerank_also_return_results(client):
    # Smoke: the two composite modes return a well-formed ranked list.
    for mode in ("hybrid", "rerank"):
        hits = _search(client, "approximate nearest neighbour search", mode, k=3)
        assert hits, f"{mode} returned no results"
        assert [h["rank"] for h in hits] == list(range(1, len(hits) + 1))
