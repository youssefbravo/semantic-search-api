"""Unit tests for the chunker. Needs the model tokenizer (transformers); skips
cleanly if it isn't installed."""
import pytest

pytest.importorskip("transformers")

from app.chunking import chunk_text, count_tokens  # noqa: E402

LONG_TEXT = (
    "Approximate nearest neighbour search trades recall for speed. "
    "HNSW builds a multi-layer proximity graph. "
    "The ef_search parameter controls the breadth of the walk. "
    "Larger values raise recall at the cost of latency. "
) * 12  # long enough to force several chunks


def test_chunks_respect_token_budget():
    max_tokens, overlap = 80, 16
    chunks = chunk_text(LONG_TEXT, max_tokens=max_tokens, overlap_tokens=overlap)
    assert len(chunks) > 1
    # Each chunk targets max_tokens; overlap may add up to overlap_tokens on top.
    for c in chunks:
        assert c.token_count <= max_tokens + overlap
        assert c.token_count == count_tokens(c.content)
        assert c.content.strip()


def test_overlap_creates_shared_content():
    chunks = chunk_text(LONG_TEXT, max_tokens=80, overlap_tokens=24)
    # With overlap, the start of a later chunk should reuse a sentence seen earlier.
    joined_first = chunks[0].content
    # at least one sentence from chunk 0 reappears at the head of chunk 1
    assert any(
        sent and sent in chunks[1].content
        for sent in joined_first.split(". ")
    )


def test_empty_and_whitespace_text():
    assert chunk_text("") == []
    assert chunk_text("   \n\n  \t ") == []


def test_single_overlong_sentence_is_hard_split():
    # No sentence punctuation -> one giant "sentence" that must be word-split.
    giant = "token " * 500
    chunks = chunk_text(giant, max_tokens=64, overlap_tokens=8)
    assert len(chunks) > 1
    for c in chunks:
        assert c.token_count <= 64 + 8
