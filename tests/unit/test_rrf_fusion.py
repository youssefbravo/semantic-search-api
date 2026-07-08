"""Unit tests for the hybrid (RRF) fusion and the rerank candidate-union logic.

These verify the *pure ranking math* of `hybrid_search` and `rerank_search` without a
database or any model: we monkeypatch the two first-stage retrievers
(`keyword_search`, `semantic_search`) to return fixed ranked lists, so the only thing
under test is the fusion / union code itself. This is the "RRF output matches a
hand-computed fusion on fixture lists" check from the audit plan.
"""
import uuid

import pytest

pytest.importorskip("sentence_transformers")  # app.search imports embeddings at module load

from app import search as search_mod  # noqa: E402
from app.search import SearchResult, hybrid_search, rerank_search  # noqa: E402

# Stable ids so we can assert on identity.
A = uuid.UUID("00000000-0000-0000-0000-00000000000a")
B = uuid.UUID("00000000-0000-0000-0000-00000000000b")
C = uuid.UUID("00000000-0000-0000-0000-00000000000c")
D = uuid.UUID("00000000-0000-0000-0000-00000000000d")
DOC = uuid.UUID("00000000-0000-0000-0000-0000000000d0")


def _mk(ids: list[uuid.UUID]) -> list[SearchResult]:
    """Build a ranked list (rank is 1-based, matching production)."""
    return [
        SearchResult(chunk_id=cid, document_id=DOC, content=f"c-{cid}", score=0.0, rank=i + 1)
        for i, cid in enumerate(ids)
    ]


def test_rrf_matches_hand_computed_fusion(monkeypatch):
    # bm25 ranks: A(1) B(2) C(3) ; semantic ranks: B(1) D(2) A(3)
    bm25 = _mk([A, B, C])
    semantic = _mk([B, D, A])
    monkeypatch.setattr(search_mod, "keyword_search", lambda db, q, k: bm25)
    monkeypatch.setattr(search_mod, "semantic_search", lambda db, q, k, qvec=None: semantic)

    rrf_k = search_mod.settings.rrf_k  # 60 by default (RRF paper constant)

    # Hand-computed RRF scores: score(d) = Σ 1 / (rrf_k + rank_in_list(d))
    expected_score = {
        A: 1 / (rrf_k + 1) + 1 / (rrf_k + 3),
        B: 1 / (rrf_k + 2) + 1 / (rrf_k + 1),
        C: 1 / (rrf_k + 3),
        D: 1 / (rrf_k + 2),
    }
    # By value, B (agreed high by both) edges out A; single-signal C/D trail.
    expected_order = [B, A, D, C]

    out = hybrid_search(db=None, query="anything", k=10)

    assert [r.chunk_id for r in out] == expected_order
    for r in out:
        assert r.score == pytest.approx(expected_score[r.chunk_id])
    # ranks are re-emitted 1-based in fused order
    assert [r.rank for r in out] == [1, 2, 3, 4]


def test_rrf_agreement_beats_single_strong_signal(monkeypatch):
    # A is #1 in BM25 but absent from semantic; B is #2 in both -> agreement wins.
    monkeypatch.setattr(search_mod, "keyword_search", lambda db, q, k: _mk([A, B]))
    monkeypatch.setattr(search_mod, "semantic_search", lambda db, q, k, qvec=None: _mk([D, B]))
    out = hybrid_search(db=None, query="q", k=10)
    # B present in both (1/62 + 1/62) beats A present once at rank1 (1/61).
    assert out[0].chunk_id == B


def test_rerank_sees_union_not_fused_topk(monkeypatch):
    """The 'hardest bug' fix: a semantic-only candidate must reach the reranker.

    If rerank operated on hybrid's fused top-k, a strong semantic-only passage could be
    voted below the cutoff before the cross-encoder ever saw it. rerank_search must
    instead pass the UNION of both retrievers' candidates to the reranker.
    """
    semantic_only = D
    monkeypatch.setattr(search_mod, "keyword_search", lambda db, q, k: _mk([A, B, C]))
    monkeypatch.setattr(
        search_mod, "semantic_search", lambda db, q, k, qvec=None: _mk([semantic_only])
    )

    seen_passages = {}

    def fake_rerank(query, passages):
        seen_passages["contents"] = list(passages)
        # Give the semantic-only candidate the top score to prove it can win.
        return [100.0 if p == f"c-{semantic_only}" else 1.0 for p in passages]

    monkeypatch.setattr(search_mod, "rerank", fake_rerank)

    out = rerank_search(db=None, query="q", k=5)

    # The semantic-only candidate was in the pool handed to the cross-encoder...
    assert f"c-{semantic_only}" in seen_passages["contents"]
    # ...and, scored highest, it surfaces at rank 1 — impossible if we'd reranked a
    # BM25-dominated fused list that dropped it.
    assert out[0].chunk_id == semantic_only


def test_rerank_empty_candidates_returns_empty(monkeypatch):
    monkeypatch.setattr(search_mod, "keyword_search", lambda db, q, k: [])
    monkeypatch.setattr(search_mod, "semantic_search", lambda db, q, k, qvec=None: [])
    # rerank must not even be called when there are no candidates.
    monkeypatch.setattr(
        search_mod, "rerank", lambda q, p: pytest.fail("rerank called with no candidates")
    )
    assert rerank_search(db=None, query="q", k=5) == []
