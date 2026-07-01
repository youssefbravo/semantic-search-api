# Load Balancing

A load balancer sits in front of several identical server instances and spreads
incoming requests across them. It is the component that makes horizontal scaling
possible: when one server is not enough, you add more and let the balancer distribute
traffic, rather than buying a single bigger machine.

The simplest distribution strategy is round robin, which sends each new request to the
next server in turn. It is trivial to implement and works well when requests cost about
the same and servers are equally powerful, but it ignores how busy each server actually
is.

A smarter strategy is least connections, which routes each request to the server
currently handling the fewest active connections. This adapts to uneven request costs,
steering traffic away from a server that is bogged down by a few slow requests toward
ones that are more idle.

To avoid sending traffic to a server that has crashed, a load balancer runs periodic
health checks, probing each backend and removing any that fail to respond from the
rotation until they recover. This is what lets the system tolerate the failure of an
individual instance without the user noticing.

Some applications need successive requests from the same user to reach the same server,
for example because session state lives there. Sticky sessions pin a client to one
backend to satisfy this, but they work against even distribution and are a sign that
the application would scale better if it were made stateless instead.
