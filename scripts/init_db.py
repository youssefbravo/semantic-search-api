"""Initialise the database: extensions, tables, and the HNSW + BM25 indexes.

Run once after Postgres is up:
    python -m scripts.init_db

Idempotent — safe to re-run.
"""
from sqlalchemy import text

from app import models  # noqa: F401  registers tables on Base.metadata
from app.db import Base, engine


def init() -> None:
    # Extensions: pgvector (semantic) + pg_search/ParadeDB BM25 (lexical).
    # The paradedb image ships both, but CREATE EXTENSION is still required per-db.
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_search"))

    Base.metadata.create_all(engine)

    with engine.begin() as conn:
        # HNSW index for approximate-nearest-neighbour semantic search.
        # vector_cosine_ops because embeddings are L2-normalized (cosine == dot).
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw "
                "ON chunks USING hnsw (embedding vector_cosine_ops)"
            )
        )
        # ParadeDB BM25 index over chunk content for true lexical search.
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS chunks_bm25 ON chunks "
                "USING bm25 (id, content) WITH (key_field='id')"
            )
        )

    print("DB initialised: extensions + tables + HNSW + BM25 indexes.")


if __name__ == "__main__":
    init()
