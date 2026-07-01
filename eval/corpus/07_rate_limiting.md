# Rate Limiting Algorithms

Rate limiting protects a service by capping how many requests a single client may
make in a given time window. It prevents accidental overload from a buggy client and
deliberate abuse from a malicious one, and it keeps shared resources fair when many
clients compete for them.

The simplest approach is a fixed window counter. Time is divided into equal windows,
such as one minute, and each client has a counter that increments on every request
and resets at the window boundary. It is easy to implement but suffers from a burst
problem: a client can send a full window of requests just before the boundary and
another full window just after, briefly doubling the intended rate.

The sliding window algorithm fixes this by considering the request timestamps within
the trailing period rather than snapping to fixed boundaries. It smooths out the
edge-of-window burst, giving a more accurate limit, at the cost of tracking more
state per client.

The token bucket algorithm takes a different view. Each client has a bucket that
refills with tokens at a steady rate up to a maximum capacity, and every request must
remove one token to proceed. Because the bucket can hold several tokens, the token
bucket algorithm allows short bursts up to the bucket capacity while still enforcing a
steady average rate over time.

A closely related variant is the leaky bucket, which processes queued requests at a
constant outflow rate regardless of how bursty the arrivals are. Where the token
bucket permits bursts, the leaky bucket deliberately smooths them into a steady stream.

In a distributed service, the rate limiter's state must be shared across all
instances, otherwise each instance enforces its own separate limit. Storing the
counters in Redis gives every instance a single source of truth, and Redis can apply
the increment and expiry atomically so concurrent requests cannot corrupt the count.
