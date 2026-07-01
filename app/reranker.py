from functools import lru_cache

from sentence_transformers import CrossEncoder

from .config import get_settings

settings = get_settings()


@lru_cache
def get_reranker() -> CrossEncoder:
    # Cross-encoder: unlike the bi-encoder embedder, it reads (query, passage)
    # TOGETHER and outputs a single relevance score. Much more accurate per pair,
    # but O(candidates) model calls — hence used only as a second-stage reranker
    # over a small candidate pool, never over the whole corpus.
    return CrossEncoder(settings.reranker_model_name)


def rerank(query: str, passages: list[str]) -> list[float]:
    if not passages:
        return []
    scores = get_reranker().predict([(query, p) for p in passages])
    return [float(s) for s in scores]
