"""Full end-to-end test against a LIVE connector. Loads ALL 45 skills + exercises every tool.
Usage: python tests/test_full.py [url]
"""
from __future__ import annotations
import asyncio, json, sys, time
from fastmcp import Client

URL = sys.argv[1] if len(sys.argv) > 1 else "https://rrizwan98-lara-marketing-connector.hf.space/mcp"
_P = _F = 0


def check(label, cond, extra=""):
    global _P, _F
    if cond:
        _P += 1; print(f"  PASS  {label}")
    else:
        _F += 1; print(f"  FAIL  {label}   {extra}")


def data_of(result):
    for a in ("data", "structured_content"):
        v = getattr(result, a, None)
        if isinstance(v, dict):
            return v
    c = getattr(result, "content", None)
    if c and getattr(c[0], "text", None):
        try:
            return json.loads(c[0].text)
        except json.JSONDecodeError:
            return {"_text": c[0].text}
    return {}


async def main():
    t0 = time.time()
    print(f"Connecting to {URL}\n")
    async with Client(URL) as client:
        tools = await client.list_tools()
        check("13 tools exposed", len(tools) == 13, f"got {len(tools)}")

        h = data_of(await client.call_tool("health", {}))
        check("health ok", h.get("ok") is True)
        check("health reports 45 skills", h.get("skills") == 45, f"got {h.get('skills')}")

        s = data_of(await client.call_tool("begin_session", {}))
        token = s.get("session_token", "")
        check("begin_session ok + token", s.get("ok") and bool(token))
        check("persona is Lara (polite female)", "Lara" in s.get("persona", ""))
        check("mandatory rules >= 4", len(s.get("mandatory_rules", [])) >= 4)
        check("router_map > 40 entries", len(s.get("router_map", {})) > 40)
        check("skills_available == 45 (max tier)", len(s.get("skills_available", [])) == 45)

        cat = data_of(await client.call_tool("domain_list_skills", {"session_token": token}))
        catalog = cat.get("skills", [])
        check("catalog has 45 skills", len(catalog) == 45, f"got {len(catalog)}")

        # ---- LOAD ALL 45 SKILLS (the complete skills test) ----
        print("\n  Loading all 45 skills from the live server...")
        names = [c["folder"] for c in catalog]
        loaded, chars, missing = 0, 0, []
        for n in names:
            g = data_of(await client.call_tool("domain_get_skill", {"session_token": token, "name": n}))
            body = g.get("body", "") if g.get("ok") else ""
            if body and len(body) > 200 and f"name: {n}" in body:
                loaded += 1; chars += len(body)
            else:
                missing.append(n)
        check(f"ALL 45 skills loaded with valid bodies", loaded == 45, f"loaded={loaded}, missing={missing}")
        print(f"     -> {loaded}/45 skills, {chars:,} total chars of instructions")

        # ---- router intelligence ----
        cases = {
            "write homepage copy for my SaaS": ["copywriting"],
            "improve my signup conversion rate": ["signup", "cro"],
            "plan a product launch next month": ["launch"],
            "reduce subscription churn": ["churn-prevention"],
            "do an SEO audit of my site": ["seo-audit"],
            "create a referral program": ["referrals"],
        }
        print("\n  Router test:")
        for task, exp in cases.items():
            r = data_of(await client.call_tool("domain_route_task", {"session_token": token, "task": task}))
            got = r.get("skills", [])
            check(f"route '{task[:32]}...' -> {exp}", any(e in got for e in exp), f"got {got}")

        # ---- per-client memory flow ----
        print("\n  Client context + history:")
        sv = data_of(await client.call_tool("user_save_client_context",
                     {"session_token": token, "client": "FullTestCo", "context_md": "# FullTestCo\nB2B SaaS for clinics."}))
        check("save client context", sv.get("ok") is True)
        gc = data_of(await client.call_tool("user_get_client_context", {"session_token": token, "client": "FullTestCo"}))
        check("read client context back", "clinics" in (gc.get("context_md") or ""))
        lc = data_of(await client.call_tool("user_list_clients", {"session_token": token}))
        check("client appears in list", "FullTestCo" in lc.get("clients", []))
        await client.call_tool("user_log_deliverable", {"session_token": token, "client": "FullTestCo", "note": "E2E test deliverable"})
        hist = data_of(await client.call_tool("user_get_history", {"session_token": token, "client": "FullTestCo"}))
        check("history records deliverable", len(hist.get("deliverables", [])) >= 1)
        prof = data_of(await client.call_tool("user_get_profile", {"session_token": token}))
        check("profile ok (tier=max)", prof.get("ok") and prof.get("tier") == "max")

        # ---- security / fail-closed ----
        print("\n  Security:")
        ns = data_of(await client.call_tool("user_list_clients", {"session_token": ""}))
        check("no session -> fail closed", ns.get("ok") is False and ns.get("error") == "session_required")
        bad = data_of(await client.call_tool("domain_get_skill", {"session_token": token, "name": "../../etc/passwd"}))
        check("path traversal blocked", bad.get("ok") is False and bad.get("error") == "not_found")

    dt = time.time() - t0
    print(f"\n{'='*50}\n  {_P} passed, {_F} failed   ({dt:.1f}s)\n{'='*50}")
    sys.exit(1 if _F else 0)


if __name__ == "__main__":
    asyncio.run(main())
