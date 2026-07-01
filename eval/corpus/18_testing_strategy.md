# Testing Strategy

Automated tests let a team change code with confidence that they have not broken
existing behaviour. But not all tests are equal in cost or value, and a good strategy
is about choosing the right mix rather than writing as many tests as possible.

A useful mental model is the test pyramid. At the base sit many fast unit tests, in the
middle fewer integration tests, and at the top a small number of slow end-to-end tests.
The shape reflects that cheap, focused tests should vastly outnumber expensive,
broad ones.

A unit test exercises a single function or class in isolation, often mocking external
dependencies so the test neither touches a database nor makes a network call. This
isolation makes unit tests fast and pinpoints failures precisely, but it means they
cannot catch problems in how components fit together.

An integration test fills that gap by exercising several components together, for
example hitting a real API endpoint backed by a real database. It is slower and needs
more setup, but it verifies the wiring that unit tests deliberately stub out, which is
where many real bugs actually live.

The enemy of a trustworthy suite is a flaky test, one that passes and fails
nondeterministically without any code change, often because it depends on timing or
external state. Flaky tests erode trust until people ignore failures entirely, so they
should be fixed or removed rather than retried. Shared setup is provided through
fixtures, reusable scaffolding that prepares the state a test needs and tears it down
afterward.
