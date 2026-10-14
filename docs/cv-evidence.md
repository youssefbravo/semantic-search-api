# CV evidence checklist

The existing CV was read locally; private contact details and the PDF are not copied here.
Its semantic-search entry says it compares keyword, meaning-based and combined search,
uses background processing, and includes a small evaluation dataset. These are supportable.

| Potential statement | Evidence | Boundaries |
|---|---|---|
| Built an AI-assisted document retrieval app | FastAPI routes, Next.js UI, screenshot | Explain AI assistance and your own contribution honestly |
| Integrated pretrained embeddings and reranking | app/embeddings.py, app/reranker.py | Do not claim training or fine-tuning |
| Combined lexical and vector ranking | app/search.py, RRF unit tests | No guarantee hybrid always wins |
| Hardened asynchronous ingestion | task locks, retry configuration, real worker verification | No exactly-once or zero-loss claim |
| Evaluated retrieval quality and latency | current report with environment/fingerprints | 22 authored documents, 59 marker-labelled queries, limited external validity |
| Implemented result caching/rate limiting | cache corpus version, Lua token bucket tests | Fail-open limits; private tenant access is absent |
| Deployed to Google Cloud | deployment files only until actual live verification | Currently pending project/budget approval; do not claim deployed |

Suggested bullet after you can explain the code:

> Built an AI-assisted FastAPI document retrieval app comparing BM25, pretrained embeddings,
> hybrid rank fusion and reranking, with Celery ingestion and a reproducible small-corpus evaluation.

Optional second bullet after reviewing the actual verification evidence:

> Added ingestion retry and duplicate-delivery checks, bounded upload reads and corpus-aware
> caching; documented recovery limits and evaluation methodology.

Before an interview, independently complete the exercise in learning.md, run a query and an
upload, explain a failure log, and identify one design tradeoff. These learning milestones
remain unverified until you perform them. Do not describe CPU throughput or ranking scores
as production results or claim sole manual authorship.
