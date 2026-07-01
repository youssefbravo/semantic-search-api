# Storage Engines: B-Trees and LSM Trees

The data structure a database uses to store and find rows on disk shapes its
performance profile. Two families dominate: B-trees, used by PostgreSQL and most
traditional relational databases, and log-structured merge trees, used by many
write-heavy NoSQL stores.

A B-tree keeps keys in a balanced, sorted structure updated in place. Looking up a key
follows a short path from the root to a leaf, so a B-tree is read-optimized and gives
fast, predictable point and range queries. The cost is that every write must find and
modify the right page on disk, which scatters random writes across the storage.

A log-structured merge tree is write-optimized instead. Incoming writes are appended to
an in-memory buffer and flushed sequentially to immutable files, turning random writes
into fast sequential ones. This makes ingestion very fast, which is why LSM engines
suit logging and time-series workloads.

The price is paid at read and maintenance time. A single key may exist in several
files, so a read may have to check multiple places, and a background process called
compaction continually merges and rewrites files to keep reads efficient and reclaim
space from deleted keys.

This rewriting introduces write amplification, where one logical write causes several
physical writes over the data's lifetime as it is compacted again and again. The
fundamental tradeoff is therefore read versus write performance: B-trees favour reads
with in-place updates, LSM trees favour writes with append-and-compact, and the right
engine depends on the workload.
