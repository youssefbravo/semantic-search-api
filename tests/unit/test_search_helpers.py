"""Unit tests for small pure helpers in the search/cache layer.

Each test imports the module it needs lazily and skips if the heavy dependency
(sentence-transformers / redis) isn't installed, so the suite stays runnable in a
minimal environment.
"""
import pytest


def test_bm25_sanitizer_strips_special_chars():
    pytest.importorskip("sentence_transformers")
    from app.search import _sanitize_bm25

    out = _sanitize_bm25('what is "BM25": term-frequency? (saturation)')
    for ch in '+:!/(){}[]^"~*?\\':
        assert ch not in out
    assert "BM25" in out and "saturation" in out


def test_bm25_sanitizer_all_special_becomes_empty():
    pytest.importorskip("sentence_transformers")
    from app.search import _sanitize_bm25

    assert _sanitize_bm25("***:::///") == ""


def test_cache_key_is_stable_and_param_sensitive():
    pytest.importorskip("redis")
    from app.cache import cache_key

    # Normalized over whitespace + case.
    assert cache_key("Hello World ", "semantic", 5) == cache_key(
        "hello world", "semantic", 5
    )
    # Sensitive to mode and k.
    assert cache_key("q", "semantic", 5) != cache_key("q", "keyword", 5)
    assert cache_key("q", "semantic", 5) != cache_key("q", "semantic", 10)
    # Stable prefix for namespacing.
    assert cache_key("q", "hybrid", 3).startswith("search:")
