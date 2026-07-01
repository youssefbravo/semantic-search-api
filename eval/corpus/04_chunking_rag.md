# Chunking Strategies for Retrieval

Before documents can be embedded, they must be split into smaller pieces called
chunks. Chunking exists because embedding models have a maximum input length, and
because a single vector for a long document averages together many unrelated topics
into one blurry representation that retrieves poorly.

The size of a chunk is a balance. Chunks that are too large dilute the embedding,
mixing the passage that answers a query with surrounding text that does not, which
lowers the similarity score. Chunks that are too small lose the surrounding context
needed to interpret them, and they fragment a single coherent answer across many
rows. Empirically a target of a few hundred tokens tends to work well.

Chunk boundaries should respect the structure of the text. A recursive splitter
tries to break on the largest natural boundary first, paragraphs, then falls back to
sentences, and only splits on words when a single sentence is itself too long. This
keeps each chunk semantically coherent instead of cutting through the middle of a
thought.

Chunking should be token-aware rather than character-aware. The model's truncation
limit is measured in tokens, not characters, so counting characters can either waste
capacity or overflow the limit. Using the model's own tokenizer to measure chunk
size guarantees that what is stored matches what the model can actually encode.

Adjacent chunks should overlap by a small amount. Without overlap, a fact that
happens to fall on a chunk boundary is split between two chunks and may be missing
from both as a coherent unit. Carrying a sentence or two of overlap from the end of
one chunk into the start of the next keeps boundary-spanning information retrievable,
at the cost of a modest increase in the number of stored chunks.

Because the best chunk size depends on the data, it should be treated as a tunable
hyperparameter and chosen by measurement rather than by guesswork. Running the same
retrieval evaluation across several chunk sizes turns an arbitrary default into a
defensible, data-driven decision.
