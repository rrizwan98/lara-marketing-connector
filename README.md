---
title: Lara Marketing Connector
emoji: 🚀
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# Lara Marketing Connector

A **remote MCP server** ("connector", AgentFactory style) that carries **Lara's full marketing
brain** — 45 marketing skills **+** the "which-skill-when" orchestration logic **+** persona +
per-client context — so any MCP host (Claude Code, Codex, OpenCode, OpenClaw, claude.ai)
connects to **one URL** and gets the complete digital-marketing employee.

Built **specs-first** — see [`specs/`](specs/). Status: **v0.1 (public/demo)**.

**Live MCP endpoint (when the Space is running):**
`https://rrizwan98-lara-marketing-connector.hf.space/mcp`

## Layout
```
lara-connector/
├── specs/            # 00-overview … 06-auth  (read these first)
├── server.py         # FastMCP gateway + all 13 tools
├── auth.py           # verified identity (demo now, OAuth seam for prod)
├── session.py        # HMAC session token (seals sub + tier)
├── db.py             # SQLite state (users, clients, deliverables, usage)
├── config_store.py   # Lara's brain: persona, rules, router map, tiers
├── skills_repo.py    # serve skills/<name>/SKILL.md (path-safe)
├── skills/           # the 45 marketing skills
├── Dockerfile        # Hugging Face Space (Docker SDK), port 7860
├── .github/workflows/deploy.yml   # test -> (pass) -> deploy to HF
└── tests/            # test_smoke.py (in-memory) + test_http.py (live)
```

## CI/CD
Push to `main` → GitHub Actions runs `tests/test_smoke.py` → **only if tests pass**, the repo is
synced to the Hugging Face Space, which rebuilds the Docker image and serves the connector.

## Run locally (demo — no sign-in, all access)
```bash
pip install -r requirements.txt
python server.py            # serves http://127.0.0.1:8000/mcp
python tests/test_smoke.py  # 16 checks
```
Defaults: `AUTH_DISABLED=1`, `GATING_ENABLED=false`, `PUBLIC_TIER=max`, SQLite.
**Set `SESSION_SIGNING_SECRET` before any public deployment.**

## The tools (13)
- **Open:** `health`, `begin_session` *(call first — returns persona, rules, router_map, skills, token)*
- **config_*:** `config_get_persona`, `config_get_rules`
- **domain_*:** `domain_list_skills`, `domain_get_skill`, `domain_route_task`
- **user_*:** `user_get_profile`, `user_list_clients`, `user_get_client_context`,
  `user_save_client_context`, `user_get_history`, `user_log_deliverable`

Every tool except `health`/`begin_session` needs the `session_token` from `begin_session`.

## Connect from a host
- **claude.ai:** Settings → Connectors → Add custom connector → paste the `/mcp` URL.
- **Claude Code / Codex:** add an MCP server pointing at the `/mcp` URL.
- **OpenClaw:** add it as an MCP server in `openclaw.json`.

## Tiers (free / pro / max)
Built in now, enforced later (see [`specs/05-tiers.md`](specs/05-tiers.md)): wire OAuth
(`AUTH_DISABLED=0`), add billing → `db.set_tier(sub, tier)`, set `GATING_ENABLED=true`.

## The 4 invariants (the book)
One gateway · tools only · identity from verified sign-in (never model args) · fail closed.
