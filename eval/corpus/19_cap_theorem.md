# The CAP Theorem and Distributed Consistency

When data is replicated across several machines, the system must make a fundamental
choice about how it behaves when those machines cannot all talk to each other. The CAP
theorem frames this choice and is one of the most cited results in distributed systems.

CAP states that a distributed data store can provide at most two of three properties:
consistency, availability, and partition tolerance. Consistency here means every read
sees the most recent write; availability means every request gets a non-error response;
partition tolerance means the system keeps working despite dropped messages between
nodes.

The subtlety is that partitions are not optional. In any real network, messages can be
lost or delayed, so partition tolerance must be assumed. That turns the theorem into a
sharper choice: during a network partition, the system must sacrifice either
consistency or availability, because it cannot have both while nodes are out of contact.

A system that chooses consistency refuses or delays requests it cannot serve correctly
until the partition heals, so clients may see errors but never stale data. A system that
chooses availability keeps answering from whatever node is reachable, accepting that
different clients may briefly see different values.

The latter approach is described as eventually consistent: once the partition heals and
updates propagate, all replicas converge on the same value. Many systems tune this with
a quorum, requiring a majority of replicas to acknowledge a read or write, which lets an
operator dial the balance between consistency and availability rather than picking one
extreme.
