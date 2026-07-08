# Architecture Diagram

Proposed Mermaid diagram for the README after human approval.

```mermaid
flowchart LR
    user["User / Frontend"] -->|"POST /documents"| api["FastAPI API"]
    user -->|"POST /search"| api
    user -->|"GET /documents/{id}"| api

    api -->|"stage raw file"| uploads["Shared uploads volume"]
    api -->|"document row + status"| pg["PostgreSQL + pgvector + ParadeDB BM25"]
    api -->|"enqueue document id + raw path"| redis["Redis broker"]
    api -->|"cache + rate limit"| redis

    redis --> celery["Celery worker"]
    uploads --> celery
    celery -->|"parse + chunk"| parser["PDF/text parser + chunker"]
    parser -->|"passages"| embed["bge-small embeddings"]
    embed -->|"vectors + text chunks"| pg

    api -->|"keyword / semantic / hybrid / rerank"| search["Search service"]
    search --> pg
    search --> reranker["bge reranker"]
    reranker --> api
    search --> api
```

Operational notes:

- Uploads return `202` quickly; ingestion is handled by Celery off the request path.
- Redis is used for queueing, cache, and the atomic token-bucket rate limiter.
- PostgreSQL is the single source of truth for document metadata, chunks, vectors, and BM25.
- Worker crash recovery depends on late acknowledgements, `prefetch=1`, and Redis visibility timeout redelivery.
