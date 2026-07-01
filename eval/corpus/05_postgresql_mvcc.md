# PostgreSQL Storage, MVCC, and Indexing

PostgreSQL is a relational database that stores rows in fixed-size blocks called
pages, each eight kilobytes by default. Understanding how it manages concurrent
access and how it finds rows quickly explains much of its performance behaviour.

Concurrency in PostgreSQL is built on multiversion concurrency control, usually
abbreviated MVCC. Instead of locking a row for readers while a writer changes it,
PostgreSQL keeps multiple versions of the row. Each transaction sees a consistent
snapshot of the database as it existed when the transaction started, so readers
never block writers and writers never block readers.

A consequence of MVCC is that an updated or deleted row is not immediately removed.
The old version remains until no running transaction can still see it, at which point
it becomes dead. These dead rows accumulate as bloat, and a background process called
autovacuum is responsible for reclaiming the space and keeping tables healthy.

To find rows without scanning an entire table, PostgreSQL uses indexes. The default
index type is a B-tree, which keeps keys in sorted order and supports equality and
range lookups efficiently. For full-text and specialized workloads, PostgreSQL also
offers GIN indexes, which map each contained element, such as a word, to the list of
rows that contain it.

PostgreSQL is extensible, which is central to this project. New data types, operators,
and even index access methods can be added through extensions without modifying the
core. The pgvector extension adds a vector type and distance operators, while the
pg_search extension adds a true BM25 index, letting a single database serve both
semantic and lexical retrieval.

The query planner decides how to execute each query, choosing between sequential
scans and the available indexes based on table statistics. When a query is slow, the
EXPLAIN ANALYZE command shows the chosen plan and the actual time spent in each step,
which is the starting point for most query optimization work.
