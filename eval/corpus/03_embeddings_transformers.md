# Text Embeddings and Transformer Encoders

A text embedding is a fixed-length vector of numbers that represents the meaning of
a piece of text. Texts with similar meaning are mapped to nearby points in the
vector space, which is what makes semantic search possible: a query and a relevant
passage end up close together even when they share no words.

Modern embeddings are produced by transformer encoder models. The input text is
split into tokens, each token is turned into a vector, and stacked self-attention
layers let every token incorporate context from the others. A pooling step then
collapses the per-token vectors into a single vector for the whole text, often by
averaging them or by taking the vector of a special classification token.

The model used in this project, bge-small-en-v1.5, produces 384-dimensional
embeddings. Smaller dimensionality keeps the index compact and queries fast, while
the model still scores competitively on retrieval benchmarks. The embeddings are L2
normalized, which means cosine similarity reduces to a simple dot product.

A subtle but important detail is that bge is an asymmetric model. Passages are
encoded as-is, but queries must be prefixed with a short instruction such as
"Represent this sentence for searching relevant passages". Omitting this prefix on
the query side silently degrades recall, because the query and passage embeddings
are then produced under mismatched conditions.

Embedding models built this way are called bi-encoders, because the query and the
document are encoded independently. This independence is what allows passage vectors
to be computed once in advance and stored in an index, so that serving a query only
requires encoding the short query and running a nearest-neighbour lookup.

Bi-encoders should not be confused with cross-encoders. A cross-encoder reads the
query and a candidate passage together in a single forward pass and outputs a
relevance score. It is far more accurate per pair but cannot be precomputed, so it
is used only to rerank a small set of candidates rather than to search the whole
collection.
