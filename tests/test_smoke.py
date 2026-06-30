"""
Smoke test — exercises the real MCP tools in-memory (no HTTP) via FastMCP's Client.
Run: python tests/test_smoke.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile

# isolate state + deterministic config BEFORE importing the server
os.environ["LARA_DB_PATH"] = os.path.join(tempfile.gettempdir(), "lara_test.db")
os.environ["AUTH_DISABLED"] = "1"
os.environ["GATING_ENABLED"] = "false"
os.environ["PUBLIC_TIER"] = "max"
os.environ["SESSION_SIGNING_SECRET"] = "test-secret"
if os.path.exists(os.environ["LARA_DB_PATH"]):
    os.remove(os.environ["LARA_DB_PATH"])

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db  # noqa: E402
import server  # noqa: E402
from fastmcp import Client  # noqa: E402

_PASS = 0
_FAIL = 0


def check(label: str, cond: bool, extra: str = "") -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  PASS  {label}")
    else:
        _FAIL += 1
        print(f"  FAIL  {label}  {extra}")


def data_of(result):
    """Get a tool's dict return across FastMCP client result shapes."""
    for attr in ("data", "structured_content"):
        v = getattr(result, attr, None)
        if isinstance(v, dict):
            return v
    content = getattr(result, "content", None)
    if content:
        first = content[0]
        text = getattr(first, "text", None)
        if text:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"_text": text}
    return {}


async def main() -> None:
    db.init_db()
    async with Client(server.mcp) as client:
        # health
        h = data_of(await client.call_tool("health", {}))
        check("health ok", h.get("ok") is True, str(h))
        check("health sees 45 skills", h.get("skills") == 45, f"got {h.get('skills')}")

        # begin_session
        s = data_of(await client.call_tool("begin_session", {}))
        check("begin_session ok", s.get("ok") is True, str(s)[:200])
        token = s.get("session_token", "")
        check("session_token present", bool(token))
        check("persona is Lara", "Lara" in s.get("persona", ""))
        check("router_map non-empty", len(s.get("router_map", {})) > 20)
        check("skills_available 45 (max tier)", len(s.get("skills_available", [])) == 45,
              f"got {len(s.get('skills_available', []))}")

        # tool without session -> fail closed
        bad = data_of(await client.call_tool("domain_list_skills", {"session_token": ""}))
        check("no session -> fail closed", bad.get("ok") is False and bad.get("error") == "session_required",
              str(bad))

        # tampered token -> session_invalid
        tampered = token[:-2] + ("aa" if not token.endswith("aa") else "bb")
        inv = data_of(await client.call_tool("domain_list_skills", {"session_token": tampered}))
        check("tampered token -> session_invalid", inv.get("ok") is False and inv.get("error") == "session_invalid",
              str(inv)[:120])

        # list skills
        ls = data_of(await client.call_tool("domain_list_skills", {"session_token": token}))
        check("list_skills 45", ls.get("ok") and len(ls.get("skills", [])) == 45,
              f"got {len(ls.get('skills', []))}")

        # route a task
        rt = data_of(await client.call_tool("domain_route_task",
                                            {"session_token": token, "task": "write homepage copy for my SaaS"}))
        check("route -> copywriting", rt.get("ok") and "copywriting" in rt.get("skills", []), str(rt))

        # get a real skill body
        gs = data_of(await client.call_tool("domain_get_skill",
                                            {"session_token": token, "name": "copywriting"}))
        check("get_skill copywriting body", gs.get("ok") and "name: copywriting" in gs.get("body", ""),
              str(gs)[:120])

        # path-traversal / unknown skill -> not_found
        nf = data_of(await client.call_tool("domain_get_skill",
                                            {"session_token": token, "name": "../secret"}))
        check("bad skill name -> not_found", nf.get("ok") is False and nf.get("error") == "not_found", str(nf))

        # save + read client context
        sv = data_of(await client.call_tool("user_save_client_context",
                                            {"session_token": token, "client": "Acme",
                                             "context_md": "# Acme\nB2B SaaS for plumbers."}))
        check("save client context", sv.get("ok") is True, str(sv))
        gc = data_of(await client.call_tool("user_get_client_context",
                                            {"session_token": token, "client": "Acme"}))
        check("read client context", gc.get("ok") and "plumbers" in (gc.get("context_md") or ""), str(gc)[:120])

        # log + history
        await client.call_tool("user_log_deliverable",
                               {"session_token": token, "client": "Acme", "note": "Wrote homepage hero."})
        hist = data_of(await client.call_tool("user_get_history", {"session_token": token, "client": "Acme"}))
        check("history has entry", hist.get("ok") and len(hist.get("deliverables", [])) == 1, str(hist)[:120])

    print(f"\n{_PASS} passed, {_FAIL} failed")
    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    asyncio.run(main())
