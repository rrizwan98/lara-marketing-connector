# Spec 06: Identity & Auth

Invariant #3 (the book): **identity comes from verified sign-in, never from model arguments.**

## Two modes (one flag: `AUTH_DISABLED`)

### Demo / public mode — `AUTH_DISABLED=1` (default for v0.1)
- No sign-in. `auth.get_principal()` returns a fixed principal:
  `{ sub: "public-demo", email: "public@lara.demo" }`.
- All callers share one "public" workspace (clients/history are shared). This is acceptable for
  the public demo; it is **documented as shared** and is the reason real multi-user needs OAuth.
- The model still cannot supply identity — the server fixes it. Invariant #3 holds.

### Production mode — `AUTH_DISABLED=0`
- The host calls the connector with an OAuth access token (Bearer JWT).
- `auth.get_principal()` verifies the token with a **four-part check** (the book):
  1. genuine — signature verifies against the issuer's JWKS,
  2. trusted issuer — `iss == AUTH_ISSUER`,
  3. stamped for us — `aud == AUTH_AUDIENCE`,
  4. not expired — `exp` in the future.
  Then `sub` (and `email`) come from the verified claims.
- Unauthenticated/invalid calls → HTTP 401.
- Discovery route: `/.well-known/oauth-protected-resource` advertises the issuer + resource so
  hosts know where to sign in. `RESOURCE_URL` is this server's public `/mcp` URL.

## Env
```
AUTH_DISABLED=1                 # v0.1 public/demo
# production:
# AUTH_DISABLED=0
# AUTH_ISSUER=https://<idp>/
# AUTH_AUDIENCE=<this server's resource id>
# RESOURCE_URL=https://<public-host>/mcp
SESSION_SIGNING_SECRET=<random 32+ bytes>
```

## Seam for implementation
`auth.py` exposes `get_principal()` returning `Principal{sub,email}`. v0.1 implements the demo
branch fully; the OAuth branch is structured with a clear `verify_jwt()` extension point (and
FastMCP's `JWTVerifier`/`RemoteAuthProvider` can be mounted on the server when `AUTH_DISABLED=0`).
Do not move identity logic into tools — keep it here.
