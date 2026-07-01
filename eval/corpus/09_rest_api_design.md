# REST API Design and HTTP Semantics

A REST API exposes resources, such as documents or users, that clients manipulate
using standard HTTP methods. The design goal is that the protocol's own verbs and
status codes carry most of the meaning, so the API behaves predictably without a
client having to learn a bespoke convention for every endpoint.

Each HTTP method has an intended meaning. GET retrieves a resource and must never
change state. POST creates a new resource or triggers an action. PUT replaces a
resource wholesale, while PATCH updates only the fields supplied. DELETE removes a
resource. Following these conventions lets caches, proxies, and other tooling reason
about requests correctly.

An important property is idempotency. An operation is idempotent by design when
performing it several times has the same effect as performing it once. GET, PUT, and
DELETE are idempotent, which is why a client can safely retry them after a network
timeout, whereas a naive POST that creates a row is not and may duplicate data on
retry.

Status codes communicate the outcome. A 201 Created response signals that a new
resource was successfully created, and conventionally includes its location. A 400
indicates a malformed request, a 404 a missing resource, and a 429 tells the client
it has been rate limited and should slow down. Using the right code is part of a
self-describing API.

REST APIs are stateless, meaning each request carries all the information needed to
process it and the server keeps no per-client session between calls. Statelessness is
what allows requests to be spread freely across many identical server instances,
because no instance holds context that another lacks.

Finally, a well-designed API is versioned, so that breaking changes can be introduced
under a new version while existing clients continue to call the old one. Versioning in
the URL path or in a header buys the freedom to evolve without breaking integrations
that were built against earlier behaviour.
