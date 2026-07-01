# Approximate Nearest Neighbour Search and HNSW

Vector databases answer similarity queries by finding the stored vectors closest to
a query vector. Doing this exactly means comparing the query against every vector in
the collection, which is a brute-force scan with linear cost in the number of items.
For small collections that is acceptable, but it does not scale to millions of
embeddings where each query would touch the entire table.

Approximate nearest neighbour (ANN) algorithms trade a small amount of recall for a
large reduction in latency. Instead of guaranteeing the exact closest neighbours,
they return vectors that are almost certainly among the closest, while inspecting
only a tiny fraction of the data. The quality of an ANN index is therefore measured
by its recall-latency curve rather than by exactness alone.

HNSW, which stands for Hierarchical Navigable Small World, is the index pgvector
uses for this project. HNSW builds a hierarchical, multi-layer proximity graph that
gives approximate nearest-neighbour search logarithmic complexity in the number of
stored vectors. The upper layers contain long-range links that let a search jump
quickly across the space, while the lower layers contain dense local links that
refine the result near the target.

A search starts at an entry point in the top layer and greedily walks toward the
query vector, descending a layer each time it can no longer get closer. The breadth
of this walk is controlled by a parameter called ef_search: a larger ef_search
inspects more candidates, which raises recall at the cost of latency. Tuning
ef_search is the main lever for moving along the recall-latency curve at query time.

HNSW is not the only option. Unlike IVFFlat, HNSW does not require a separate
training step to learn cluster centroids, and it handles incremental inserts
gracefully without needing periodic reindexing. The tradeoff is that HNSW indexes
use more memory and are slower to build, because the graph must be constructed link
by link as vectors are added.
