# Data Serialization Formats

Serialization turns an in-memory data structure into a sequence of bytes that can be
stored or sent over a network, and deserialization reconstructs it on the other side.
The choice of format trades off human readability, size, and speed.

JSON is the default for web APIs because it is human-readable and schema-less, meaning
the structure travels with the data and no separate definition is needed to parse it.
That flexibility is also its cost: field names are repeated in every record as text,
so JSON is verbose and comparatively slow to parse at high volume.

Protocol Buffers take the opposite approach. The message structure is declared once in
a schema, and the wire format is binary and compact, identifying fields by small
integer tags instead of names. The result is dramatically smaller payloads and faster
encoding, at the price of needing the schema to interpret the bytes.

A schema-based format brings a second benefit: evolution. If new fields are given new
tags and old fields are never reused, a message stays backward compatible, so a new
producer and an old consumer can still communicate. This disciplined versioning is
harder to enforce with free-form JSON.

The general rule of thumb is to use JSON at the system's edges, where humans and
external clients interact with the API, and a binary format for high-throughput
internal communication between services where size and speed dominate. The right
choice depends on whether readability or efficiency matters more at that boundary.
