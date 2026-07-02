# MCP Server for ChatGPT Apps — Server, Tools, Payloads

Source of truth: `https://developers.openai.com/apps-sdk/build/mcp-server` and
`https://developers.openai.com/api/docs/mcp`. Re-fetch before use.

## SDKs & scaffold

```bash
# TypeScript / Node
npm install @modelcontextprotocol/sdk @modelcontextprotocol/ext-apps zod
# Python
pip install mcp   # FastMCP included; FastAPI also works
```

Layout:
```
your-chatgpt-app/
├─ server/src/index.ts     # MCP server + tool handlers
├─ web/src/component.tsx   # widget source
└─ web/dist/app.{js,css}   # built bundle referenced by the server
```

## Server instructions (cross-tool guidance)

Returned during MCP initialization; ChatGPT/Codex read them with tool metadata.

```ts
const server = new McpServer(
  { name: "example-server", version: "1.0.0" },
  { instructions:
      "Before updating an item, call list_items to validate the ID. Bulk edits: max 10 per request." }
);
```
Rules: concise, most important first, **first 512 chars self-contained**; don't repeat
tool descriptions or set personality.

## Tool descriptors (the contract the model reasons about)

One tool per user intent. Each descriptor includes:
- machine name + human `title`
- `inputSchema` AND `outputSchema` (Zod raw shapes in TS helper; JSON Schema elsewhere)
- `_meta.ui.resourceUri` → the widget template URI (UI apps only)
- REQUIRED annotations:

| Hint | Set `true` when |
|---|---|
| `readOnlyHint` | tool only retrieves/computes; no create/update/delete/send |
| `openWorldHint` | (writes only) tool can hit arbitrary URLs/files; `false` for bounded targets |
| `destructiveHint` | (writes only) delete/overwrite/irreversible effects |

Missing/null hints = **validation error** — fix the definition.

```ts
registerAppTool(server, "show-board", {
  title: "Show Board",
  inputSchema: { workspace: z.string() },
  outputSchema: { columns: z.array(z.object({ id: z.string(), title: z.string(),
    items: z.array(z.object({ id: z.string(), title: z.string(), status: z.string() })) })) },
  _meta: {
    ui: { resourceUri: "ui://widget/board.html" },
    // optional ChatGPT status strings:
    // "openai/toolInvocation/invoking": "Preparing…",
    // "openai/toolInvocation/invoked": "Ready."
  },
}, async ({ workspace }) => {
  const board = await loadBoard(workspace);
  return {
    structuredContent: board.summary,                      // model + widget
    content: [{ type: "text", text: "Latest snapshot." }], // model narration
    _meta: board.details,                                  // widget only
  };
});
```

**Design handlers idempotent — the model may retry calls.**

## The three payload channels

| Channel | Model sees? | Widget sees? | Use for |
|---|---|---|---|
| `structuredContent` | ✅ | ✅ | lean summary the model narrates from |
| `content` | ✅ | ✅ | optional narration text (Markdown/plain) |
| `_meta` | ❌ never | ✅ | full datasets, widget-only detail |

Anti-pattern: full lists in `structuredContent` → model tries to summarize every item,
wastes tokens, slows rendering. Keep counts/status for the model; ship the rest in `_meta`.

## Tool visibility (who may call)

```json
"_meta": { "ui": { "resourceUri": "ui://widget/board.html", "visibility": ["model", "app"] } }
```
- default: both model and UI
- `["app"]`: callable ONLY from the widget via `tools/call` (hidden from model tool
  selection) — use for rapid UI actions (toggle, delete-selected)

## Memory (ChatGPT)

Off by default for apps; user-controlled; model-mediated. Apps see only what the model
puts in tool inputs. Therefore: explicit required inputs for correctness; treat memory
as hint; safe defaults or a follow-up question when context is missing; re-confirm
destructive parameters in the current turn.

## File handling (ChatGPT extension)

- Input files: declare `_meta["openai/fileParams"]: ["fieldName"]` (top-level fields
  only). Each file param arrives as
  `{ download_url, file_id, mime_type?, file_name? }` — `download_url` is temporary;
  use `file_id` to request fresh URLs later.
- Output files: return a file reference in `structuredContent` (e.g. `file_uri: {...}`)
  instead of inline/base64; or MCP `resource_link` content for user-visible downloads
  (ChatGPT elicits approval before downloading external `https://` resources).

## Localization & client hints

- `_meta["openai/locale"]` in requests (legacy `webplus/i18n`): RFC 4647 match, echo
  back, format accordingly.
- `_meta["openai/userAgent"]`, `_meta["openai/userLocation"]`: analytics/formatting only.
  **Never authorization.**

## Data-only apps (no UI) & company knowledge

Implement the exact `search` + `fetch` input schemas (also required for deep research
and company knowledge sources). Mark other read-only tools `readOnlyHint: true`.

`search(query: string)` returns:
```json
{ "results": [{ "id": "doc-1", "title": "…", "url": "https://example.com/doc" }] }
```
`fetch(id: string)` returns:
```json
{ "id": "doc-1", "title": "…", "text": "full text…", "url": "https://…", "metadata": {} }
```
Both: return the object as `structuredContent` AND the same JSON string in `content`
for compatibility. **Citations are created only when `url` is a non-empty, user-openable
absolute HTTP(S) URL** — keep internal IDs in `id`, not `url`.

## Run locally & expose

1. Build widget bundle → 2. start server → 3. **MCP Inspector** against
   `http://localhost:<port>/mcp` (mirrors ChatGPT's widget runtime) →
4. `ngrok http <port>` for the HTTPS URL ChatGPT requires.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Widget doesn't render | template `mimeType` must be `text/html;profile=mcp-app`; bundle URLs must resolve in sandbox |
| No `ui/*` messages | bridge enabled only for that MIME type; check CSP violations |
| CSP/CORS failures | allow exact domains in `_meta.ui.csp` |
| Stale bundle | version the template URI; update every reference |
| Model slow/verbose | trim `structuredContent` |

## Security reminders

- All payloads + widget state are user-visible → **no secrets anywhere**.
- Enforce auth in the server/backing APIs, never via client hints.
- Prompt injection is real: content reachable through tools may carry hostile
  instructions; keep write actions confirmed and scoped; report malicious servers to
  security@openai.com.
