# Widgets & ChatGPT UI — Templates, Bridge, State, React

Source of truth: `https://developers.openai.com/apps-sdk/build/chatgpt-ui`,
`/apps-sdk/build/mcp-server`, `/apps-sdk/reference`. Re-fetch before use.

## Register the UI template (server side)

A widget is an MCP **resource**: HTML text served with the MCP Apps MIME type.

```ts
import { registerAppResource, RESOURCE_MIME_TYPE } from "@modelcontextprotocol/ext-apps/server";

registerAppResource(server, "board-widget", "ui://widget/board.html", {}, async () => ({
  contents: [{
    uri: "ui://widget/board.html",
    mimeType: RESOURCE_MIME_TYPE,           // "text/html;profile=mcp-app"
    text: `
<div id="root"></div>
<style>${CSS}</style>
<script type="module">${JS}</script>`.trim(),
    _meta: {
      ui: {
        prefersBorder: true,
        domain: "https://myapp.example.com",          // required for submission; unique per app
        csp: {
          connectDomains: ["https://api.example.com"],       // fetch targets
          resourceDomains: ["https://persistent.oaistatic.com"], // static assets
          // frameDomains: [...]  // discouraged; extra review scrutiny
        },
      },
      // optional: "openai/widgetDescription": "Interactive board rendered by show-board."
    },
  }],
}));
```

- **Legacy ChatGPT aliases** (older apps/books): MIME `text/html+skybridge`, tool meta
  `_meta["openai/outputTemplate"]`, resource meta key `openai.com/widget`. ChatGPT still
  honors them; new apps should use the MCP Apps forms above.
- **Cache rule:** the URI is the cache key. Breaking change → new URI
  (`ui://widget/board-v2.html`) + update every reference (resource URI, tool
  `_meta.ui.resourceUri`, contents `uri`).

## The MCP Apps bridge (portable core)

JSON-RPC 2.0 over `postMessage`. The host delivers tool inputs/results to the iframe:

```js
window.addEventListener("message", (event) => {
  if (event.source !== window.parent) return;
  const msg = event.data;
  if (!msg || msg.jsonrpc !== "2.0") return;
  if (msg.method === "ui/notifications/tool-result") render(msg.params);
}, { passive: true });
```

- Render from `params.structuredContent` (+ widget-only detail in `params._meta`).
- Widget → server tool calls: **`tools/call`** through the bridge.
- Approval-gated tools: initial `toolInput` may be missing; the host delivers it via
  `ui/notifications/tool-input` after the user approves.

## `window.openai` (compatibility layer + ChatGPT extensions)

Use ONLY behind feature detection: `window.openai?.method?.(…)`.

| API | Purpose |
|---|---|
| `toolInput` / `toolOutput` / `widgetState` | globals mirroring current tool I/O and saved state |
| `setWidgetState(state)` | persist UI state across re-renders in the conversation |
| `callTool(name, args)` | invoke a tool (silent; no conversation turn) |
| `sendFollowUpMessage({ prompt })` | insert a user-style message → new model turn |
| `requestDisplayMode({ mode })` | `inline` \| `pip` \| `fullscreen` (mobile may coerce pip→fullscreen) |
| `requestModal({ template? })` | host-owned modal; optionally another registered template URI |
| `requestClose()` | close the widget (server-side: `openai/closeWidget: true` in response meta) |
| `uploadFile(file, { library? })` → `{ fileId }` | upload from widget |
| `selectFiles()` → `[{ fileId, fileName, mimeType }]` | pick from user's ChatGPT library (feature-detect; fall back to upload) |
| `getFileDownloadUrl({ fileId })` → `{ downloadUrl }` | temporary download URL |
| `openExternal(url)` | open external link (see `redirect_domains` to skip safe-link modal) |

Host updates globals via the `openai:set_globals` window event.
`openai/widgetSessionId` (tool response meta) correlates logs per widget instance.

## Interactivity patterns

- **Silent update** (checkbox toggle, delete selected): `tools/call` → then refresh view.
  Gate UI-only tools with `_meta.ui.visibility: ["app"]` so the model can't call them.
- **Model-mediated action** (needs reasoning/context): `sendFollowUpMessage` → model
  calls a tool → fresh `tool-result` re-renders the widget.
- Choose per action: deterministic + fast → `tools/call`; contextual → follow-up message.

## State persistence

UI state (selection, scroll, tab) dies on re-render unless saved:

1. On load: hydrate from `window.openai?.widgetState`.
2. On change: update local state, then `setWidgetState(next)` BEFORE any action that
   triggers a reload.
3. Clean dangling references (e.g., selected IDs that were deleted).

Server data (`structuredContent`/`_meta`) is authoritative; `widgetState` is only for
view state.

## Display modes & navigation

- Request more space for maps/tables/editors: `requestDisplayMode({ mode: "fullscreen" })`.
- Skybridge (the sandbox runtime) mirrors iframe history into ChatGPT — standard routing
  (e.g., React Router `BrowserRouter`) keeps host navigation controls in sync.

## React production pattern

Bundle with esbuild/Vite into a single JS (+CSS) file the template references.

```ts
// subscribe to a host global reactively
export function useOpenAiGlobal<K extends keyof Globals>(key: K) {
  return useSyncExternalStore(
    (onChange) => {
      const h = (e: SetGlobalsEvent) => { if (e.detail.globals[key] !== undefined) onChange(); };
      window.addEventListener("openai:set_globals", h, { passive: true });
      return () => window.removeEventListener("openai:set_globals", h);
    },
    () => window.openai?.[key]
  );
}
// useWidgetState: hydrate from widgetState on mount; sync via setWidgetState on change
```

Why React at scale: declarative render replaces manual DOM sync; centralized state;
reusable components; consistent styling. Vanilla HTML/JS is fine for L1–L2 widgets
(quickstart uses a single HTML file, no build step).

## Widget checklist

- [ ] Template registered with correct MIME + versioned URI
- [ ] Renders purely from bridge `tool-result` (works without `window.openai`)
- [ ] Every `window.openai` usage optional-chained + feature-detected
- [ ] UI-only tools `visibility: ["app"]`; silent vs model-mediated actions chosen deliberately
- [ ] State hydrates/saves via `widgetState`; survives re-render
- [ ] Display mode requests justified; mobile behavior verified
- [ ] No secrets in markup/state; CSP domains minimal
