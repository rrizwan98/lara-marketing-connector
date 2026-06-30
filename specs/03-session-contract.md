# Spec 03: Session Contract

## begin_session() — called first, always
Resolves the verified principal, ensures a `users` row, computes the effective tier, mints a
session token, and returns Lara's full operating contract.

### Returns
```jsonc
{
  "session_token": "<base64url(payload).base64url(hmac)>",
  "tier": "max",                       // effective tier (see 05-tiers.md)
  "persona": "<who Lara is + voice>",
  "mandatory_rules": [ "<rule>", ... ],
  "router_map": { "<task phrase>": "<skill name>", ... },
  "skills_available": [ "product-marketing", "copywriting", ... ],  // tier-filtered
  "user_state": {
    "email": "...",
    "clients": ["ClientA", ...],
    "limits": { "tasks_per_day": 200, "tasks_used_today": 12, "max_clients": 10,
                "history_days": 90, "gating_enabled": false }
  },
  "fail_closed": "If begin_session is unavailable or a tool fails, tell the user the session
                  can't continue. Do NOT improvise an answer."
}
```

### The AI's expected loop (stated inside mandatory_rules)
1. Call `begin_session()` once at the start.
2. For any marketing task → choose the skill from `router_map` (or call `domain_route_task`).
3. Call `domain_get_skill(name)` and **follow it** — never freelance from memory.
4. Load/build the client's context (`user_get_client_context`) before real work.
5. Log meaningful output with `user_log_deliverable`.

## Session token
- Format: `b64url(json(payload)) + "." + b64url(HMAC_SHA256(secret, b64url(json(payload))))`.
- Payload: `{ "sub": str, "tier": str, "iat": int, "exp": int }`. TTL default 8h.
- Secret: `SESSION_SIGNING_SECRET` (env). A dev default is used with a loud warning if unset.
- `verify(token)` checks signature (constant-time compare) and `exp`. Invalid → raise → tool
  returns fail-closed refusal.

## Why a token (not re-auth each call)
- Enforces "begin_session first".
- Carries `tier` so every tool gates without re-querying the IdP.
- Honors invariant #3: identity is sealed server-side at session start, not passed by the model.

## Fail-closed contract
Any tool that receives a missing/invalid/expired token, or hits a downed dependency, returns:
```jsonc
{ "ok": false, "error": "session_required" | "session_invalid" | "unavailable" | "limit_reached" | "forbidden",
  "message": "<human reason>" }
```
The persona/rules tell the AI to surface this and stop — not to fabricate.
