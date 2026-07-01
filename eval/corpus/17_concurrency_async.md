# Concurrency: Threads versus Async

Concurrency is about structuring a program to make progress on many tasks at once. The
right approach depends on what the tasks spend their time doing, and the central
distinction is whether work is I/O-bound or CPU-bound.

An I/O-bound task spends most of its time waiting, for a network response, a disk read,
or a database query, rather than computing. While one task waits, the program could be
doing useful work on another. This is exactly the situation asynchronous programming is
designed for.

Async concurrency runs on a single thread driven by an event loop. When a task starts
waiting on I/O, it yields control back to the event loop, which runs other ready tasks
in the meantime and resumes the first when its result arrives. Because there is only
one thread, there are no locks and no context-switch overhead, but a single long
computation will block everything.

CPU-bound work is the opposite: it keeps a processor busy and never waits, so yielding
gains nothing. Speeding it up requires running on multiple cores in parallel. In some
runtimes this is complicated by a global interpreter lock, which permits only one
thread to execute bytecode at a time, so true parallelism needs separate processes.

This is why the design of this project keeps the embedding work, which is CPU-bound, in
a separate worker process rather than on the API's event loop. The API stays responsive
to many concurrent requests, while the heavy computation runs where it cannot stall
them. Matching the concurrency model to the workload is the whole point.
