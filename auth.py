"""
auth.py — resolve the VERIFIED principal. Identity never comes from model arguments.

v0.1 (AUTH_DISABLED=1): a fixed public/demo principal.
Production (AUTH_DISABLED=0): verify the OAuth bearer JWT with the book's four-part check.

See specs/06-auth.md.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Principal:
    sub: str
    email: str


class AuthError(Exception):
    """Raised when a request is unauthenticated/invalid in production mode (-> HTTP 401)."""


def _auth_disabled() -> bool:
    return os.environ.get("AUTH_DISABLED", "1").strip().lower() in ("1", "true", "yes", "on")


DEMO_PRINCIPAL = Principal(
    sub=os.environ.get("DEMO_SUB", "public-demo"),
    email=os.environ.get("DEMO_EMAIL", "public@lara.demo"),
)


def get_principal(token: str | None = None) -> Principal:
    """Return the verified Principal for this call.

    In demo mode the server fixes the identity (the model still cannot supply it).
    In production the server passes the request's bearer token; we verify it here.
    """
    if _auth_disabled():
        return DEMO_PRINCIPAL
    if not token:
        raise AuthError("missing bearer token")
    claims = verify_jwt(token)
    return Principal(sub=claims["sub"], email=claims.get("email", ""))


def verify_jwt(token: str) -> dict:
    """Four-part check (genuine, trusted issuer, stamped for us, not expired).

    Requires `pyjwt[crypto]` and AUTH_ISSUER / AUTH_AUDIENCE set. Implemented as the
    production seam; not exercised in v0.1 demo mode.
    """
    issuer = os.environ.get("AUTH_ISSUER")
    audience = os.environ.get("AUTH_AUDIENCE")
    if not issuer or not audience:
        raise AuthError("AUTH_ISSUER / AUTH_AUDIENCE not configured")
    try:
        import jwt  # PyJWT (lazy import; only needed in production)
        from jwt import PyJWKClient
    except ImportError as exc:  # noqa: BLE001
        raise AuthError("pyjwt[crypto] is required when AUTH_DISABLED=0") from exc

    jwks_url = os.environ.get("AUTH_JWKS_URL", issuer.rstrip("/") + "/.well-known/jwks.json")
    signing_key = PyJWKClient(jwks_url).get_signing_key_from_jwt(token).key
    return jwt.decode(
        token,
        signing_key,
        algorithms=["RS256", "ES256"],
        audience=audience,       # 3) stamped for us
        issuer=issuer,           # 2) trusted issuer
        options={"require": ["exp", "sub"]},  # 4) not expired (+ identity present)
    )  # 1) genuine — signature verified against the issuer's JWKS
