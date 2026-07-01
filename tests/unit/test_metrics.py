"""Unit tests for the benchmark metrics — pure functions, run anywhere."""
import math

import pytest

from eval.metrics import ndcg_at_k, precision_at_k, recall_at_k, reciprocal_rank


def test_precision_at_k():
    retrieved = ["a", "b", "c", "d"]
    relevant = {"a", "c"}
    assert precision_at_k(retrieved, relevant, 2) == pytest.approx(0.5)  # [a,b]
    assert precision_at_k(retrieved, relevant, 4) == pytest.approx(0.5)  # 2/4
    assert precision_at_k([], relevant, 5) == 0.0


def test_recall_at_k():
    retrieved = ["a", "b", "c", "d"]
    relevant = {"a", "c", "e"}  # 'e' never retrieved
    assert recall_at_k(retrieved, relevant, 4) == pytest.approx(2 / 3)
    assert recall_at_k(retrieved, relevant, 1) == pytest.approx(1 / 3)  # only 'a'
    assert recall_at_k(retrieved, set(), 4) == 0.0  # no relevant -> defined as 0


def test_reciprocal_rank():
    assert reciprocal_rank(["a", "b", "c"], {"b", "c"}) == pytest.approx(0.5)  # rank 2
    assert reciprocal_rank(["x", "y", "z"], {"z"}) == pytest.approx(1 / 3)
    assert reciprocal_rank(["a"], {"zzz"}) == 0.0


def test_ndcg_perfect_and_partial():
    # Perfect: both relevant items ranked first -> nDCG == 1.
    assert ndcg_at_k(["a", "b", "c"], {"a", "b"}, 3) == pytest.approx(1.0)
    # One relevant item at rank 2: DCG = 1/log2(3), IDCG = 1/log2(2) = 1.
    expected = (1.0 / math.log2(3)) / 1.0
    assert ndcg_at_k(["a", "b"], {"b"}, 2) == pytest.approx(expected)
    assert ndcg_at_k(["a", "b"], set(), 2) == 0.0


def test_ndcg_rewards_higher_rank():
    relevant = {"hit"}
    high = ndcg_at_k(["hit", "x", "y"], relevant, 3)
    low = ndcg_at_k(["x", "y", "hit"], relevant, 3)
    assert high > low
