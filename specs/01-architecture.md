# Spec 01: Architecture

## The 4 invariants (the book) — and how we honor them
1. **One gateway.** A single FastMCP server, stateless streamable HTTP, mounted at `/mcp`.
2. **Tools only.** No MCP resources, no MCP prompts. Skills are returned as tool *outputs*.
3. **Identity from verified sign-in, never from model arguments.** Tools never accept a
   `user`/`sub`. Identity is resolved server-side (OAuth `sub` in production; a fixed demo
   principal when `AUTH_DISABLED=1`) and carried in a signed **session token** minted by
   `begin_session()`.
4. **Fail closed.** If a session is invalid, a dependency is down, or a limit is hit, the tool
   returns a clear refusal. The AI is instructed (in the session contract) to stop, not improvise.

## Components
| File | Responsibility |
|------|----------------|
| `server.py` | FastMCP gateway; declares every tool; wires auth → session → db → skills |
| `auth.py` | Resolve the verified principal (demo principal, or OAuth-verified `sub`) |
| `session.py` | Mint + verify the HMAC-signed session token (carries `sub`, `tier`, `exp`) |
| `db.py` | SQLite (dev/demo) state: users, user_state, clients, deliverables, usage |
| `config_store.py` | Lara's brain: persona, mandatory rules, router map, tier definitions |
| `skills_repo.py` | Read `skills/*/SKILL.md`: list catalog + return one skill's body (path-safe) |
| `skills/` | The 45 marketing `SKILL.md` folders (the served knowledge) |

## Request flow
```
host (AI) ──/mcp──> FastMCP gateway
   1. begin_session()        auth.principal -> db.get_or_create_user -> tier
                             -> session.mint(token) -> returns brain + token
   2. domain_/user_ tool(session_token, ...)
                             session.verify(token) -> {sub, tier}
                             -> (gating check) -> db / skills_repo -> result
                             -> on any failure: fail-closed refusal
```

## Tech stack
- **Python 3.10+** (book recommends 3.14; 3.12 used here). **FastMCP** (streamable HTTP).
- **State:** SQLite via stdlib `sqlite3` for dev/demo. Production swaps `DATABASE_URL` to
  **Neon/Postgres** (same function surface in `db.py`).
- **Session token:** stdlib `hmac`/`hashlib` (no external dep).
- **Frontmatter parsing:** PyYAML.
- **Config:** `python-dotenv` (`.env`).
- **Deploy:** Cloudflare tunnel → public HTTPS URL ending in `/mcp`.

## Why this travels everywhere
Skills + the "which-skill-when" logic both live in the server. Any MCP host connects by URL and
calls `begin_session()` first; everything else follows from the returned contract.
