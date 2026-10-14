from functools import lru_cache

from sentence_transformers import CrossEncoder

from .config import get_settings

settings = get_settings()


@lru_cache
def get_reranker() -> CrossEncoder:
    # Cross-encoder: unlike the bi-encoder embedder, it reads (query, passage)
    # TOGETHER and outputs a single relevance score. Joint attention can improve
    # ranking, but inference cost grows with candidate count — hence used only
    # over a small candidate pool, never over the whole corpus. The pinned model's
    # default activation is sigmoid; its score is not a calibrated probability.
    return CrossEncoder(settings.reranker_model_name,
                        revision=settings.reranker_model_revision, max_length=512)


def rerank(query: str, passages: list[str]) -> list[float]:
    if not passages:
        return []
    scores = get_reranker().predict([(query, p) for p in passages])
    return [float(s) for s in scores]
