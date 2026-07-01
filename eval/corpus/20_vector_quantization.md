# Vector Quantization and Compression

Storing millions of high-dimensional embeddings in memory is expensive. A single
384-dimensional vector in 32-bit floats takes over a kilobyte, so a hundred million of
them run to hundreds of gigabytes. Quantization compresses these vectors so that far
more fit in memory, trading a little accuracy for a large saving.

The simplest method is scalar quantization, which stores each dimension in fewer bits,
for example as an 8-bit integer instead of a 32-bit float. This immediately cuts the
size to a quarter with only a small loss of precision, because the exact magnitude of
each component rarely needs full floating-point resolution for similarity ranking.

A more aggressive method is product quantization. It splits each vector into several
sub-vectors, clusters the possible sub-vectors into a small codebook, and stores only
the codebook index for each piece. Because a whole sub-vector collapses to a single
byte-sized code, product quantization reduces memory by an order of magnitude or more.

All of these techniques are forms of lossy compression: the original vector cannot be
reconstructed exactly, only approximated. As a result recall drops slightly, since the
distances computed on compressed vectors are estimates and occasionally rank a true
neighbour just below the cutoff.

The practical pattern is to combine compression with a refinement step. A quantized
index quickly produces a shortlist of candidates from the whole collection, and then
the system re-scores just those candidates using the full-precision vectors. This
recovers most of the lost accuracy while keeping the memory footprint of the large
index small.
