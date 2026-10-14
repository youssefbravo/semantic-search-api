from functools import lru_cache

from sentence_transformers import SentenceTransformer

from .config import get_settings

settings = get_settings()


@lru_cache
def get_model() -> SentenceTransformer:
    # Lazy + cached per process. Loads once on first use (first Celery task in the
    # worker, first query in the API). CPU inference is fine for bge-small.
    return SentenceTransformer(settings.embedding_model_name,
                               revision=settings.embedding_model_revision)


def embed_passages(texts: list[str]) -> list[list[float]]:
    """Embed chunks for storage. Passages get NO prefix (bge asymmetry)."""
    model = get_model()
    for passage in texts:
        if len(model.tokenizer.encode(passage)) > model.max_seq_length:
            raise ValueError("Passage exceeds embedding model token limit")
    vecs = model.encode(
        texts,
        normalize_embeddings=True,  # so cosine distance == dot product
        batch_size=32,
        show_progress_bar=False,
    )
    return [v.tolist() for v in vecs]


def embed_query(text: str) -> list[float]:
    """Embed a search query. Queries MUST carry the retrieval instruction prefix."""
    model = get_model()
    if len(model.tokenizer.encode(settings.query_prefix + text)) > model.max_seq_length:
        raise ValueError("Query exceeds embedding model token limit including prefix")
    vec = model.encode(
        settings.query_prefix + text,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return vec.tolist()
