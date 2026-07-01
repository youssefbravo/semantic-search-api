# Distance Metrics for Vector Similarity

Semantic search ranks passages by how close their embedding is to the query's
embedding, which raises the question of what "close" means. Several distance and
similarity measures are common, and the right one depends on how the embeddings were
produced.

Euclidean distance is the straight-line distance between two points, the measure most
people picture geometrically. It is sensitive to magnitude: two vectors pointing the
same direction but with different lengths are considered far apart, even if they
represent the same meaning at different intensities.

Cosine similarity instead measures the angle between two vectors and ignores their
magnitude entirely. This is usually what you want for text, because a passage's meaning
should not depend on its length or how emphatically it is written, only on the direction
its embedding points. Cosine ranges from minus one to one, where one means identical
direction.

The dot product multiplies the vectors component by component and sums the result. It
blends both direction and magnitude, so on its own it is affected by vector length. The
key relationship is that for normalized vectors, where every vector is scaled to unit
length, the dot product equals the cosine similarity exactly.

This equivalence is why this project normalizes its embeddings at encoding time. With
unit-length vectors, the database can use a fast dot-product or inner-product operation
and get cosine ranking for free, avoiding the extra work of computing magnitudes at
query time while still ignoring length the way text similarity should.
