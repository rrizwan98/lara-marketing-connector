"""Live ChatGPT-App-layer test against the deployed connector.
Verifies: version, widget resource + MIME, tool _meta (std + alias), text-only tools,
and that plain-MCP behavior (Claude/Codex mode) is unchanged.
Usage: python tests/test_live_app.py [url]
"""
from __future__ import annotations
import asyncio, json, sys
from fastmcp import Client

URL = sys.argv[1] if len(sys.argv) > 1 else "https://rrizwan98-lara-marketing-connector.hf.space/mcp"
WIDGET_URI = "ui://widget/lara-v1.html"
_P = _F = 0


def check(label, cond, extra=""):
    global _P, _F
    if cond: _P += 1; print(f"  PASS  {label}")
    else: _F += 1; print(f"  FAIL  {label}   {extra}")


def data_of(r):
    for a in ("data", "structured_content"):
        v = getattr(r, a, None)
        if isinstance(v, dict): return v
    c = getattr(r, "content", None)
    if c and getattr(c[0], "text", None):
        try: return json.loads(c[0].text)
        except json.JSONDecodeError: return {"_text": c[0].text}
    return {}


async def main():
    print(f"Connecting to {URL}\n")
    async with Client(URL) as client:
        h = data_of(await client.call_tool("health", {}))
        check("live version is 0.2.0 (new deploy)", h.get("version") == "0.2.0", f"got {h.get('version')}")
        check("45 skills served", h.get("skills") == 45)

        tools = await client.list_tools()
        check("13 tools (unchanged for Claude/Codex)", len(tools) == 13, f"got {len(tools)}")
        by = {t.name: t for t in tools}

        def meta(t):
            d = t.model_dump(by_alias=True)
            return d.get("_meta") or d.get("meta") or {}

        for n in ("begin_session", "domain_list_skills", "domain_route_task", "domain_get_skill"):
            m = meta(by[n])
            check(f"{n}: widget linked (std+alias)",
                  (m.get("ui") or {}).get("resourceUri") == WIDGET_URI
                  and m.get("openai/outputTemplate") == WIDGET_URI, str(m)[:120])
        m = meta(by["user_get_profile"])
        check("user_get_profile: text-only", "ui" not in m and "openai/outputTemplate" not in m)

        res = await client.read_resource(WIDGET_URI)
        first = res[0] if isinstance(res, list) else res.contents[0]
        mime = getattr(first, "mimeType", None) or getattr(first, "mime_type", None)
        html = getattr(first, "text", "") or ""
        check("widget resource served", len(html) > 1000, f"len={len(html)}")
        check("widget MIME mcp-app", mime == "text/html;profile=mcp-app", f"got {mime}")
        check("widget: bridge + legacy handlers", "ui/notifications/tool-result" in html and "openai:set_globals" in html)

        # plain-MCP behavior unchanged (what Claude/Codex see)
        s = data_of(await client.call_tool("begin_session", {}))
        tok = s.get("session_token", "")
        check("begin_session works (persona+token)", s.get("ok") and "Lara" in s.get("persona", "") and bool(tok))
        r = data_of(await client.call_tool("domain_route_task", {"session_token": tok, "task": "write homepage copy"}))
        check("route -> copywriting", "copywriting" in r.get("skills", []), str(r)[:100])
        g = data_of(await client.call_tool("domain_get_skill", {"session_token": tok, "name": "ads"}))
        check("get_skill ads body", g.get("ok") and len(g.get("body", "")) > 5000)

    print(f"\n{_P} passed, {_F} failed")
    sys.exit(1 if _F else 0)


if __name__ == "__main__":
    asyncio.run(main())
