# Observability: Logs, Metrics, and Traces

Once a system is distributed across many services and machines, you can no longer
understand a failure by reading a single console. Observability is the practice of
instrumenting a system so its internal state can be inferred from the outside, and it
rests on what are often called the three pillars: logs, metrics, and traces.

Logs are timestamped records of discrete events. Structured logging, where each entry
is emitted as machine-readable key-value data rather than a free-form sentence, is what
makes logs searchable and aggregatable at scale, so you can filter millions of lines to
the handful relevant to an incident.

Metrics are numeric measurements sampled over time, such as request rate, error rate,
and latency percentiles. Unlike logs, metrics are aggregated into time series, which
makes them cheap to store and ideal for dashboards and alerting thresholds that fire
when a number crosses a danger line.

The hardest question in a distributed system is following one user request as it fans
out across many services. Distributed tracing answers it by attaching a correlation id
to the request at the edge and propagating it through every downstream call, so all the
work done on that request's behalf can later be stitched back together.

Used together, the pillars are complementary: a metric alerts you that error rate has
spiked, a trace shows you which service in the chain is responsible, and its logs tell
you exactly what went wrong there. None of the three alone is enough, which is why
mature systems invest in all of them.
