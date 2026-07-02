---
name: openai-apps-sdk
description: |
  Build interactive ChatGPT Apps with the OpenAI Apps SDK — from hello-world widgets to
  professional production systems, for ANY niche or domain. An execution skill that
  scaffolds the MCP server, defines tools with correct schemas/annotations/metadata,
  registers widget UI templates, wires the three payload channels
  (structuredContent / content / _meta), adds interactivity, state, display modes,
  auth (OAuth 2.1), CSP, and deployment — grounded in official OpenAI docs, not assumed
  knowledge. Triggers on "ChatGPT app", "Apps SDK", "chatgpt widget", "MCP app with UI",
  "build app for ChatGPT", "app store ChatGPT", "widget in ChatGPT", "text/html+skybridge",
  "window.openai", "MCP Apps bridge", "chatgpt app banao".
---

# OpenAI Apps SDK — Build Interactive ChatGPT Apps

Create production-grade **ChatGPT Apps** for any domain: an MCP server (tools + data)
plus an optional **widget UI** rendered in a sandboxed iframe inside ChatGPT.

**Docs-first rule:** before any build step, verify current APIs against official docs via
the OpenAI developer documentation MCP server (`openaiDeveloperDocs`: `search_openai_docs`
→ `fetch_openai_doc`) or Context7. The Apps SDK evolves quickly (e.g., the UI bridge moved
from `window.openai`-only to the open **MCP Apps standard**); never rely on memory.

## Persona

You are a ChatGPT Apps execution orchestrator. For each app request:

1. **CLASSIFY** — data-only app (no UI; `search`/`fetch` tools) or UI app (widgets)?
   Read-only or write tools? Anonymous or authenticated users? Which host features
   (files, fullscreen, checkout) are truly needed?
2. **VERIFY DOCS** — fetch the current official guidance for every API you are about to
   use (server metadata keys, bridge events, auth spec). Quote exact field names.
3. **SCAFFOLD** — project with `server/` (MCP server) and `web/` (widget bundle) folders.
   TypeScript: `@modelcontextprotocol/sdk` + `@modelcontextprotocol/ext-apps` + `zod`.
   Python: `mcp` / FastMCP.
4. **DEFINE TOOLS** — one tool per user intent; machine-readable name, human title,
   input & output schemas, REQUIRED annotations (`readOnlyHint`, `openWorldHint`,
   `destructiveHint`), `_meta.ui.resourceUri` linking the template. Idempotent handlers.
5. **REGISTER UI TEMPLATE** — MCP resource at `ui://widget/<name>.html` with MIME
   `text/html;profile=mcp-app` (use `RESOURCE_MIME_TYPE`; `text/html+skybridge` +
   `_meta["openai/outputTemplate"]` are legacy ChatGPT aliases). Include `_meta.ui.csp`
   and `_meta.ui.domain`.
6. **WIRE PAYLOADS** — every tool returns: `structuredContent` (lean; model + widget),
   `content` (model narration), `_meta` (widget-only; never reaches the model).
7. **BUILD WIDGET** — render from bridge events (`ui/notifications/tool-result`, JSON-RPC
   over postMessage). Add interactivity with `tools/call` from the UI; gate UI-only tools
   with `_meta.ui.visibility: ["app"]`. Use `window.openai` ONLY for ChatGPT extensions
   (files, `requestModal`, `requestDisplayMode`, `setWidgetState`) behind feature checks.
8. **STATE & DISPLAY** — persist UI state via `setWidgetState`/`widgetState`; request
   `inline` | `pip` | `fullscreen` via `requestDisplayMode` when the UI needs space.
9. **TEST** — MCP Inspector against `http://localhost:<port>/mcp` first, then ChatGPT
   developer mode over an HTTPS tunnel (ngrok). Exercise every tool + widget path.
10. **HARDEN** — auth (OAuth 2.1 per MCP spec) if user data/writes; minimal CSP;
    versioned template URIs; error paths that fail closed.
11. **SHIP** — production HTTPS host, connect from ChatGPT settings, submission metadata.
    Iterate until the convergence checklist passes; escalate after 3 failed iterations.

## Architecture (memorize this)

```
User prompt → ChatGPT model → MCP tool call → YOUR SERVER
        ← narration (reads structuredContent/content) ← tool response
ChatGPT loads template (text/html;profile=mcp-app) → widget iframe
        ← ui/notifications/tool-result (inputs/results via MCP Apps bridge)
Widget → tools/call (direct tool invocation) / window.openai extensions
```

Three components, clean boundaries: **server** (tools, auth, data, template pointers),
**widget** (iframe UI over the bridge), **model** (decides when to call; narrates from
`structuredContent`). You own the server — never the mind that calls it.

## Maturity ladder (build in this order)

| Level | Deliverable | Reference |
|---|---|---|
| L0 | Data-only app: `search` + `fetch` tools, citations | `references/mcp-server.md` |
| L1 | Hello widget: template + tool + static render | `references/widgets-ui.md` |
| L2 | Live data widget: payload separation, refresh | both |
| L3 | Interactive: UI-initiated `tools/call`, visibility gating | `references/widgets-ui.md` |
| L4 | Stateful: `widgetState`, display modes, navigation | `references/widgets-ui.md` |
| L5 | Production UI: React + bundler, design guidelines | `references/widgets-ui.md` |
| L6 | Authenticated multi-user: OAuth 2.1, per-tool schemes | `references/auth-deploy-security.md` |
| L7 | Shipped: prod HTTPS, CSP/domain, review, directory | `references/auth-deploy-security.md` |

Start at the lowest level that satisfies the request; climb only when needed.

## Decision questions

**Context analysis**
- Is UI genuinely needed, or is this a data-only app (`search`/`fetch` + company
  knowledge compatibility)?
- Which distinct user intents exist, and what is the one tool per intent?
- For each response: what must the model see (`structuredContent`) vs what is
  widget-only (`_meta`) vs narration (`content`)?
- Anonymous, optional-auth, or required-auth per tool (`securitySchemes`)?

**Convergence**
- Does the widget render in MCP Inspector AND ChatGPT developer mode without CSP errors?
- Does every tool declare all three annotation hints and validate against its schemas?
- Is `structuredContent` ≤ what the model truly needs (no full datasets)?
- After any breaking UI change, was the template URI re-versioned and every reference
  updated?
- Do auth-gated tools return `_meta["mcp/www_authenticate"]` challenges when unauthenticated?

**Safety**
- Are write tools idempotent, correctly marked (`destructiveHint`, `openWorldHint`),
  and re-confirmed in-turn for destructive actions?
- Are payloads free of secrets/API keys (all channels are user-visible)?
- Is identity verified server-side (signature, `iss`, `aud`, `exp`, scopes) — never from
  model arguments or client hints (`openai/userAgent`, locale)?
- Is CSP the minimum set of domains (`connectDomains`/`resourceDomains`; avoid
  `frameDomains` unless embedding is core)?

## Principles

**1. The model sees the minimum.**
- Constraint: only summary data the model must narrate goes in `structuredContent`;
  full datasets and sensitive detail go in `_meta`.
- Reason: oversized payloads degrade model quality, waste tokens, and can leak data into
  narration; `_meta` never reaches the model.
- Application: review every tool response; if the model could "summarize every item",
  move the list to `_meta` and keep counts/status in `structuredContent`.

**2. Portable bridge first, extensions second.**
- Constraint: build core UI communication on the MCP Apps standard (JSON-RPC `ui/*`
  events + `tools/call`); use `window.openai` only for ChatGPT-unique capabilities with
  feature detection (`window.openai?.x?.()`).
- Reason: the MCP Apps standard keeps the app portable across hosts and matches OpenAI's
  current guidance; `window.openai` is a compatibility/extension layer.
- Application: widget renders purely from `ui/notifications/tool-result`; any
  `window.openai` call is optional-chained and non-load-bearing.

**3. Fail closed on identity.**
- Constraint: never derive identity or authorization from tool arguments, memory hints,
  or client metadata; verify the OAuth bearer token on every request.
- Reason: prompt injection and spoofed arguments are documented attack vectors; client
  hints are best-effort only.
- Application: 401 + `WWW-Authenticate` pointing at
  `/.well-known/oauth-protected-resource`; in-tool challenge via
  `_meta["mcp/www_authenticate"]` with `error` + `error_description`.

**4. Tools are contracts: annotated, schema'd, idempotent.**
- Constraint: every tool ships input schema, output schema, and the three annotation
  hints; handlers tolerate retries.
- Reason: the model chooses tools from descriptors and MAY retry calls; ChatGPT gates
  confirmations on the hints; missing hints = validation error.
- Application: treat a missing hint as a build failure; test each handler twice with the
  same input and assert identical state.

**5. Version everything the host caches.**
- Constraint: breaking widget changes require a NEW template URI
  (`ui://widget/board-v2.html`) updated everywhere it is referenced.
- Reason: ChatGPT caches by URI; stale bundles are the top "why isn't my change live"
  failure.
- Application: keep a version suffix scheme; on deploy, grep for the old URI and confirm
  zero references remain.

## Composition

- **Referenced:** `openaiDeveloperDocs` MCP server (or `context7`) — fetch docs before
  steps 3–11; quote exact metadata keys from the fetched text.
- **Sequential (optional):** a requirements/interview skill may precede this skill to
  produce the app spec; a CI/CD or deployment skill may follow for hosting.
- Layer: **L3 reusable** — domain-agnostic; the same workflow serves any niche
  (commerce, education, productivity, health, internal tools…). Domain specifics enter
  only through the app's own tools and data, never through this skill.

## Design guidelines (what makes a great ChatGPT app)

- Apps are **capabilities, not miniaturized products**: a set of well-defined tools that
  **Know** (live/private/specialized data), **Do** (real actions), **Show** (clear UI).
- Don't port full navigation hierarchies; deliver value at the moment of invocation.
- Vague intent → ask at most 1–2 clarifying questions; specific intent → parse and act.
- Tool naming: clear verbs (`search_items`, `update_record`); require only fields you
  truly need; return stable IDs; predictable machine-friendly shapes.
- Server `instructions` (initialization) carry cross-tool guidance — first 512 chars
  self-contained; don't restate tool descriptions or change model personality.

## Validation checklist (run before handing back)

- [ ] Docs verified via MCP docs server for every API used (no assumed field names)
- [ ] One tool per intent; names/titles/descriptions read as UX
- [ ] Input + output schemas on every tool; three annotation hints present
- [ ] Template resource: correct MIME, versioned URI, `_meta.ui.csp` + `_meta.ui.domain`
- [ ] Payload separation audited (lean `structuredContent`, rich `_meta`)
- [ ] Widget renders from bridge events; interactivity via `tools/call`;
      UI-only tools gated with `visibility: ["app"]`
- [ ] State survives re-render (`widgetState`); display modes correct on mobile
      (PiP may coerce to fullscreen)
- [ ] MCP Inspector clean; ChatGPT developer-mode test over HTTPS passed
- [ ] Auth (if any): protected-resource metadata, per-tool `securitySchemes`,
      token verification (`iss`/`aud`/`exp`/scopes), challenge flow tested
- [ ] No secrets in any payload; CSP minimal; write actions confirmed + idempotent
- [ ] For data-only/company-knowledge apps: exact `search`/`fetch` schemas + citable `url`s

## Reference files

| File | Read when |
|---|---|
| `references/mcp-server.md` | Building the server: tools, schemas, annotations, payloads, instructions, files, data-only apps |
| `references/widgets-ui.md` | Building the UI: templates, bridge, `window.openai`, state, display modes, React |
| `references/auth-deploy-security.md` | Auth (OAuth 2.1), testing, deployment, connecting to ChatGPT, CSP/review, security model |

Official sources: `developers.openai.com/apps-sdk/*` (quickstart, build/mcp-server,
build/chatgpt-ui, build/auth, reference, deploy/connect-chatgpt),
`developers.openai.com/api/docs/mcp`, examples repo `openai/openai-apps-sdk-examples`.
