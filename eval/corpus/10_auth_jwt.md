# Authentication with JSON Web Tokens

Authentication establishes who is making a request, and authorization decides what
they are allowed to do. A common way to carry an authenticated identity through a
stateless API is the JSON Web Token, a compact, self-contained credential that the
server issues after a successful login.

A JSON Web Token has three parts: a header, a payload, and a signature, each base64url
encoded and separated by dots. The user's identity and permissions are stored in the
payload as claims, such as the subject identifier, an expiry timestamp, and any roles.
Because the parts are merely encoded, anyone can read them.

This leads to the single most misunderstood point about the format: a token is signed
but not encrypted. The signature lets the server verify that the claims were issued by
it and have not been tampered with, but it does nothing to hide them. Secrets must
never be placed in the payload, because any holder of the token can decode and read it.

To limit the damage if a token leaks, systems issue a short-lived access token used on
every request together with a longer-lived refresh token kept more securely. When the
access token expires after a few minutes, the client exchanges the refresh token for a
new one, so a stolen access token is only useful for a brief window.

Because verification only requires checking a signature, any server instance can
validate a token without a database lookup or shared session store. This is what makes
token authentication scale horizontally so well, and it is the same statelessness
property that REST APIs rely on elsewhere.

The tradeoff is revocation. Since the token is valid until it expires, instantly
invalidating one before its expiry requires extra machinery such as a deny list,
which partly gives back the simplicity that made stateless tokens attractive in the
first place.
