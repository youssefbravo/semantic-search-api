# Task Queues and Celery

A task queue moves slow work out of the request-response path so that an API can
respond immediately while the heavy lifting happens in the background. Uploading a
document and embedding all of its chunks can take many seconds, which is far too long
to make an HTTP client wait, so the work is handed off to a queue instead.

The pattern has three parts. A producer, here the FastAPI upload endpoint, places a
message describing the work onto a queue. A broker holds the queue durably. A worker,
running as a separate process, pulls messages off the queue and executes the
corresponding task. Because the worker is decoupled, it can be scaled independently of
the API.

Celery is the task queue framework used in this project. The producer calls a task's
delay method, which serializes the arguments and enqueues a message rather than
running the function inline. One or more Celery worker processes consume those
messages and run the task, completely outside the web server's request cycle.

The broker is the durable middleman between producer and worker. This project uses
Redis as the broker, so an enqueued task survives even if no worker is currently
available, and is picked up as soon as one is. Keeping large payloads out of the
broker matters: the upload task passes a file path on a shared volume rather than the
file's bytes, because brokers are meant for small messages.

Tasks should be designed to be idempotent and retryable, because a worker can crash
midway or a message can be delivered more than once. If a task fails, Celery can retry
it a bounded number of times, and writing the task so that repeating it causes no harm
makes these retries safe.

Observability matters once work is asynchronous, because failures no longer surface
directly in the HTTP response. The ingestion task records its progress on the document
row, moving it through pending, processing, and finally done or failed, so a client
can poll the document's status endpoint to learn the outcome.
