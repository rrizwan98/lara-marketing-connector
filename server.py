"""
server.py — Lara Marketing Connector (FastMCP gateway).

One gateway, tools only, identity from the session token (sealed at begin_session),
fail-closed. Skills + the "which-skill-when" logic are served from here so they travel
to any MCP host by URL.

Run (demo):  python server.py     (uses AUTH_DISABLED=1, SQLite, gating off)
See specs/ for the full contract.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

import auth
import config_store
import db
import session
import skills_repo
from fastmcp import FastMCP

VERSION = "0.1.0"
GATING_ENABLED = os.environ.get("GATING_ENABLED", "false").strip().lower() in ("1", "true", "yes", "on")
PUBLIC_TIER = os.environ.get("PUBLIC_TIER", "max")
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))
TRANSPORT = os.environ.get("LARA_TRANSPORT", "http")

mcp = FastMCP("lara-marketing")


# --------------------------------------------------------------------------- #
# helpers (centralized session + gating, so behavior is consistent everywhere)
# --------------------------------------------------------------------------- #

def _err(error: str, message: str) -> dict:
    return {"ok": False, "error": error, "message": message}


def _open_session(token: str):
    """Return (payload, None) on success, or (None, error_dict) — fail-closed."""
    if not token:
        return None, _err("session_required", "Call begin_session() first and pass session_token.")
    try:
        return session.verify(token), None
    except session.SessionError as exc:
        return None, _err("session_invalid", str(exc))


def _effective_tier_for_user(user: dict) -> str:
    return user.get("tier", "free") if GATING_ENABLED else PUBLIC_TIER


# --------------------------------------------------------------------------- #
# open tools (no session)
# --------------------------------------------------------------------------- #

@mcp.tool
def health() -> dict:
    """Liveness check. No identity or state. Returns server name, version, gating flag."""
    return {"ok": True, "name": "lara-marketing", "version": VERSION,
            "gating_enabled": GATING_ENABLED, "skills": skills_repo.count()}


@mcp.tool
def begin_session() -> dict:
    """START HERE. Open a Lara session and receive her operating contract: persona, the
    mandatory rules, the task->skill router map, the skills available to you, your saved
    clients, and a session_token. You MUST pass that session_token to every other tool."""
    principal = auth.get_principal()  # demo: fixed public identity; prod: OAuth-verified
    user = db.get_or_create_user(principal.sub, principal.email)
    tier = _effective_tier_for_user(user)
    token = session.mint(principal.sub, tier)
    limits = config_store.limits_for_tier(tier)
    return {
        "ok": True,
        "session_token": token,
        "tier": tier,
        "persona": config_store.PERSONA,
        "mandatory_rules": config_store.MANDATORY_RULES,
        "router_map": config_store.ROUTER_MAP,
        "skills_available": config_store.skills_for_tier(tier),
        "user_state": {
            "email": user.get("email", ""),
            "clients": db.list_clients(principal.sub),
            "limits": {
                **limits,
                "tasks_used_today": db.get_usage_today(principal.sub),
                "gating_enabled": GATING_ENABLED,
            },
        },
        "fail_closed": config_store.FAIL_CLOSED,
    }


# --------------------------------------------------------------------------- #
# config_* (brain re-fetch)
# --------------------------------------------------------------------------- #

@mcp.tool
def config_get_persona(session_token: str) -> dict:
    """Re-fetch Lara's persona/voice mid-session."""
    payload, err = _open_session(session_token)
    if err:
        return err
    return {"ok": True, "persona": config_store.PERSONA}


@mcp.tool
def config_get_rules(session_token: str) -> dict:
    """Re-fetch Lara's mandatory rules and the fail-closed contract."""
    payload, err = _open_session(session_token)
    if err:
        return err
    return {"ok": True, "mandatory_rules": config_store.MANDATORY_RULES,
            "fail_closed": config_store.FAIL_CLOSED}


# --------------------------------------------------------------------------- #
# domain_* (skills now; real tools later)
# --------------------------------------------------------------------------- #

@mcp.tool
def domain_list_skills(session_token: str) -> dict:
    """List the marketing skills catalog (name, description, category). 'allowed' reflects
    your tier. Use this, or domain_route_task, to choose a skill for the task."""
    payload, err = _open_session(session_token)
    if err:
        return err
    tier = payload["tier"]
    skills = []
    for c in skills_repo.get_catalog():
        skills.append({**c, "allowed": config_store.is_skill_allowed(tier, c["folder"])})
    return {"ok": True, "skills": skills}


@mcp.tool
def domain_get_skill(session_token: str, name: str) -> dict:
    """Get the FULL instructions (SKILL.md body) for one marketing skill, then follow them.
    Call this for every marketing task after choosing the skill. Counts as one task."""
    payload, err = _open_session(session_token)
    if err:
        return err
    sub, tier = payload["sub"], payload["tier"]
    if GATING_ENABLED:
        if not config_store.is_skill_allowed(tier, name):
            return _err("forbidden", f"The '{name}' skill is not in the {tier} tier.")
        limit = config_store.limits_for_tier(tier)["tasks_per_day"]
        if limit != -1 and db.get_usage_today(sub) >= limit:
            return _err("limit_reached", f"Daily task limit ({limit}) reached for the {tier} tier.")
    if not skills_repo.valid_skill(name):
        return _err("not_found", f"No skill named '{name}'. Use domain_list_skills to see names.")
    body = skills_repo.get_skill_body(name)
    if body is None:
        return _err("unavailable", f"Skill '{name}' could not be read.")
    db.incr_usage(sub)
    return {"ok": True, "name": name, "body": body}


@mcp.tool
def domain_route_task(session_token: str, task: str) -> dict:
    """Suggest the best skill(s) for a free-text marketing task using the router map.
    A cheap helper that does not consume your daily task quota."""
    payload, err = _open_session(session_token)
    if err:
        return err
    if not task or not task.strip():
        return _err("bad_input", "Provide a task description.")
    words = set(w for w in "".join(c if c.isalnum() else " " for c in task.lower()).split() if len(w) > 2)
    scored: dict[str, int] = {}
    for phrase, skill in config_store.ROUTER_MAP.items():
        pwords = set(phrase.lower().split())
        score = len(words & pwords)
        if skill in task.lower():
            score += 3
        if score:
            scored[skill] = max(scored.get(skill, 0), score)
    ranked = [s for s, _ in sorted(scored.items(), key=lambda kv: kv[1], reverse=True)]
    if not ranked:
        ranked = ["marketing-ideas"]
        rationale = "No direct match — start from marketing-ideas or product-marketing."
    else:
        rationale = "Matched against the router map. Read the top skill with domain_get_skill."
    return {"ok": True, "skills": ranked[:3], "rationale": rationale}


# --------------------------------------------------------------------------- #
# user_* (per-user, keyed by verified sub from the token)
# --------------------------------------------------------------------------- #

@mcp.tool
def user_get_profile(session_token: str) -> dict:
    """Return the caller's email, tier, client count, and limits/usage."""
    payload, err = _open_session(session_token)
    if err:
        return err
    sub, tier = payload["sub"], payload["tier"]
    user = db.get_user(sub) or {"email": ""}
    return {"ok": True, "email": user.get("email", ""), "tier": tier,
            "clients_count": db.count_clients(sub),
            "limits": {**config_store.limits_for_tier(tier),
                       "tasks_used_today": db.get_usage_today(sub)}}


@mcp.tool
def user_list_clients(session_token: str) -> dict:
    """List the caller's saved marketing clients."""
    payload, err = _open_session(session_token)
    if err:
        return err
    return {"ok": True, "clients": db.list_clients(payload["sub"])}


@mcp.tool
def user_get_client_context(session_token: str, client: str) -> dict:
    """Get a client's product-marketing context (Markdown), or null if not set yet."""
    payload, err = _open_session(session_token)
    if err:
        return err
    if not client or not client.strip():
        return _err("bad_input", "Provide a client name.")
    ctx = db.get_client_context(payload["sub"], client.strip())
    return {"ok": True, "client": client.strip(), "context_md": ctx}


@mcp.tool
def user_save_client_context(session_token: str, client: str, context_md: str) -> dict:
    """Create or update a client's product-marketing context. Build this with the
    product-marketing skill before doing real work for a client."""
    payload, err = _open_session(session_token)
    if err:
        return err
    sub, tier = payload["sub"], payload["tier"]
    client = (client or "").strip()
    if not client:
        return _err("bad_input", "Provide a client name.")
    if not isinstance(context_md, str):
        return _err("bad_input", "context_md must be text.")
    if GATING_ENABLED and not db.client_exists(sub, client):
        max_clients = config_store.limits_for_tier(tier)["max_clients"]
        if max_clients != -1 and db.count_clients(sub) >= max_clients:
            return _err("limit_reached",
                        f"The {tier} tier allows {max_clients} client(s). Upgrade for more.")
    db.save_client_context(sub, client, context_md)
    return {"ok": True, "client": client}


@mcp.tool
def user_get_history(session_token: str, client: str, limit: int = 10) -> dict:
    """Get recent deliverables/notes for a client (the 'previous work' memory)."""
    payload, err = _open_session(session_token)
    if err:
        return err
    sub, tier = payload["sub"], payload["tier"]
    client = (client or "").strip()
    if not client:
        return _err("bad_input", "Provide a client name.")
    history_days = config_store.limits_for_tier(tier)["history_days"] if GATING_ENABLED else None
    since = None if (history_days is None or history_days == -1) else history_days
    rows = db.list_deliverables(sub, client, limit=max(1, min(limit, 50)), since_days=since)
    return {"ok": True, "client": client, "deliverables": rows}


@mcp.tool
def user_log_deliverable(session_token: str, client: str, note: str) -> dict:
    """Record a one-line note about a deliverable you produced for a client."""
    payload, err = _open_session(session_token)
    if err:
        return err
    client = (client or "").strip()
    note = (note or "").strip()
    if not client or not note:
        return _err("bad_input", "Provide both client and note.")
    db.log_deliverable(payload["sub"], client, note)
    return {"ok": True}


# --------------------------------------------------------------------------- #
# entrypoint
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    db.init_db()
    print(f"[lara] starting connector v{VERSION} on {HOST}:{PORT}{'/mcp'} "
          f"(transport={TRANSPORT}, gating={GATING_ENABLED}, auth_disabled={auth._auth_disabled()})")
    mcp.run(transport=TRANSPORT, host=HOST, port=PORT)
