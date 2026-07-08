from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Postgres ---
    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/semantic_search"
    )

    # --- Redis / Celery ---
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    redis_visibility_timeout_seconds: int = 300

    # --- Embedding model ---
    # bge-small-en-v1.5: 384-dim, ~33M params, MIT licence, strong MTEB retrieval
    # scores at a fraction of the size of base models. Runs on CPU.
    embedding_model_name: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
    # bge is ASYMMETRIC: passages stored raw, queries carry this instruction prefix.
    # Omitting it on queries silently tanks recall.
    query_prefix: str = "Represent this sentence for searching relevant passages: "

    # --- Reranker (phase 3) ---
    reranker_model_name: str = "BAAI/bge-reranker-base"

    # --- Search ---
    # Hybrid: pull this many candidates from EACH of BM25 + semantic before fusing.
    hybrid_pool: int = 50
    # RRF constant. 60 is the value from the original RRF paper; dampens the weight
    # of any single ranker so no list dominates.
    rrf_k: int = 60
    # Rerank: first-stage retrieves this many candidates for the cross-encoder.
    rerank_pool: int = 30

    # --- Chunking ---
    # ~400 tokens leaves headroom under the model's 512 cap (after the query prefix
    # + special tokens); 60-token overlap keeps boundary-spanning facts retrievable.
    chunk_max_tokens: int = 400
    chunk_overlap_tokens: int = 60

    # --- Caching ---
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300  # bound how stale a cached result can be
    metrics_enabled: bool = True

    # --- Rate limiting (token bucket) ---
    rate_limit_enabled: bool = True
    rate_limit_capacity: int = 30        # burst: max tokens in the bucket
    rate_limit_refill_per_sec: float = 1.0  # sustained: tokens added per second

    # --- CORS (so the browser frontend can call the API) ---
    cors_origins: list[str] = ["*"]

    # --- Uploads ---
    upload_dir: str = "./data/uploads"
    max_upload_mb: int = 25
    ingest_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
