"""Ranking metrics for the benchmark. All use binary relevance.

`retrieved` is an ordered list of chunk ids (rank 1 first); `relevant` is the set of
ids judged relevant for the query.
"""
import math
from collections.abc import Hashable, Sequence


def precision_at_k(retrieved: Sequence[Hashable], relevant: set, k: int) -> float:
    """Fraction of the top-k that are relevant."""
    top = retrieved[:k]
    if not top:
        return 0.0
    return sum(1 for r in top if r in relevant) / len(top)


def recall_at_k(retrieved: Sequence[Hashable], relevant: set, k: int) -> float:
    """Fraction of all relevant items that appear in the top-k."""
    if not relevant:
        return 0.0
    top = set(retrieved[:k])
    return len(top & relevant) / len(relevant)


def reciprocal_rank(retrieved: Sequence[Hashable], relevant: set) -> float:
    """1 / rank of the first relevant hit (0 if none). Averaged across queries = MRR."""
    for i, r in enumerate(retrieved, start=1):
        if r in relevant:
            return 1.0 / i
    return 0.0


def _dcg(gains: Sequence[float]) -> float:
    return sum(g / math.log2(i + 1) for i, g in enumerate(gains, start=1))


def ndcg_at_k(retrieved: Sequence[Hashable], relevant: set, k: int) -> float:
    """Normalized discounted cumulative gain — rewards relevant hits ranked higher.

    With binary relevance the ideal ranking puts all min(|relevant|, k) hits first,
    so IDCG is the DCG of that ideal list.
    """
    if not relevant:
        return 0.0
    gains = [1.0 if r in relevant else 0.0 for r in retrieved[:k]]
    idcg = _dcg([1.0] * min(len(relevant), k))
    if idcg == 0.0:
        return 0.0
    return _dcg(gains) / idcg
