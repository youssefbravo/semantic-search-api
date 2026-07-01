# Caching with Redis

Caching stores the result of an expensive operation so that repeated requests for the
same thing can be served quickly from memory instead of being recomputed. In a search
service, embedding a query and running retrieval costs real time, so caching the
results of identical queries is an easy and large win.

Redis is an in-memory data store often used as a cache because reads and writes
complete in well under a millisecond. In this project Redis plays three roles at
once: it is the Celery message broker, the backend that stores task results, and the
cache for repeated search queries, which keeps the number of moving parts small.

A cache needs a key that uniquely identifies the request. For search, the key is
built from the query text, the search mode, and the number of results requested, so
that two genuinely identical searches hit the cache while a change in any parameter
misses it and is computed fresh.

Cached entries should not live forever, because the underlying documents change as
new ones are ingested. Setting a time-to-live, or TTL, on each cache entry makes it
expire automatically after a chosen interval, bounding how stale a served result can
be without requiring any explicit invalidation logic.

When the cache fills up, Redis must decide what to evict. A least-recently-used
policy, abbreviated LRU, discards the entries that have gone longest without being
accessed, on the assumption that recently used items are the most likely to be used
again. This keeps the hottest queries resident while cold ones fall out.

Two failure modes are worth knowing. A cache stampede happens when a popular entry
expires and many requests recompute it simultaneously; it is mitigated by locking or
by staggering expirations. Caching is also only safe for idempotent reads, so the
search endpoint is a natural fit while document uploads, which change state, are not.
