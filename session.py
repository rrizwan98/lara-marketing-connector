"""
session.py — mint and verify the HMAC-signed session token.

The token seals identity (sub) + tier server-side at begin_session() time, so later tools
never trust the model for identity (invariant #3). See specs/03-session-contract.md.

Token = b64url(json(payload)) + "." + b64url(HMAC_SHA256(secret, b64url(json(payload))))
payload = {"sub", "tier", "iat", "exp"}
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time

_DEV_DEFAULT = "dev-insecure-change-me"
SECRET = os.environ.get("SESSION_SIGNING_SECRET", _DEV_DEFAULT)
DEFAULT_TTL = int(os.environ.get("SESSION_TTL_SECONDS", str(8 * 3600)))

if SECRET == _DEV_DEFAULT:
    # Loud warning, but do not crash dev/demo runs.
    print("[session] WARNING: SESSION_SIGNING_SECRET is unset — using an insecure dev secret. "
          "Set a strong random value before any public deployment.")


class SessionError(Exception):
    """Raised when a token is missing, malformed, tampered, or expired."""


def _b64u_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64u_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def _sign(payload_b64: str) -> str:
    mac = hmac.new(SECRET.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256)
    return _b64u_encode(mac.digest())


def mint(sub: str, tier: str, ttl: int = DEFAULT_TTL) -> str:
    now = int(time.time())
    payload = {"sub": sub, "tier": tier, "iat": now, "exp": now + ttl}
    payload_b64 = _b64u_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    return f"{payload_b64}.{_sign(payload_b64)}"


def verify(token: str) -> dict:
    if not token or not isinstance(token, str) or "." not in token:
        raise SessionError("session token missing or malformed")
    payload_b64, sig = token.rsplit(".", 1)
    expected = _sign(payload_b64)
    # constant-time comparison to prevent signature forgery via timing
    if not hmac.compare_digest(sig, expected):
        raise SessionError("session token signature invalid")
    try:
        payload = json.loads(_b64u_decode(payload_b64))
    except Exception as exc:  # noqa: BLE001
        raise SessionError("session token payload invalid") from exc
    if int(payload.get("exp", 0)) < int(time.time()):
        raise SessionError("session token expired")
    if "sub" not in payload or "tier" not in payload:
        raise SessionError("session token incomplete")
    return payload
