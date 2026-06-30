"""Live HTTP client test — connects to a running connector like a real MCP host would.
Usage: python tests/test_http.py [url]   (default http://127.0.0.1:8765/mcp)
"""
import asyncio
import json
import sys

from fastmcp import Client

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765/mcp"


def data_of(result):
    for attr in ("data", "structured_content"):
        v = getattr(result, attr, None)
        if isinstance(v, dict):
            return v
    content = getattr(result, "content", None)
    if content and getattr(content[0], "text", None):
        try:
            return json.loads(content[0].text)
        except json.JSONDecodeError:
            return {"_text": content[0].text}
    return {}


async def main():
    async with Client(URL) as client:
        tools = await client.list_tools()
        print(f"connected to {URL}")
        print(f"tools exposed: {len(tools)} -> {', '.join(t.name for t in tools)}")

        h = data_of(await client.call_tool("health", {}))
        print(f"health: ok={h.get('ok')} skills={h.get('skills')} version={h.get('version')}")

        s = data_of(await client.call_tool("begin_session", {}))
        token = s.get("session_token", "")
        print(f"begin_session: ok={s.get('ok')} tier={s.get('tier')} "
              f"skills_available={len(s.get('skills_available', []))} token={'yes' if token else 'no'}")

        r = data_of(await client.call_tool("domain_route_task",
                                           {"session_token": token, "task": "5 email welcome sequence"}))
        print(f"route '5 email welcome sequence' -> {r.get('skills')}")

        g = data_of(await client.call_tool("domain_get_skill",
                                           {"session_token": token, "name": "emails"}))
        body = g.get("body", "")
        print(f"get_skill emails: ok={g.get('ok')} body_chars={len(body)}")
        print("\nLIVE HTTP TEST OK" if (h.get("ok") and token and g.get("ok")) else "\nLIVE HTTP TEST FAILED")


if __name__ == "__main__":
    asyncio.run(main())
