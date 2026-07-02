# Auth, Deployment & Security — ChatGPT Apps

Source of truth: `https://developers.openai.com/apps-sdk/build/auth`,
`/apps-sdk/deploy/connect-chatgpt`, `/api/docs/mcp`. Re-fetch before use.

## When auth is required

Read-only anonymous apps can skip auth. Anything exposing **customer-specific data or
write actions must authenticate users** via OAuth 2.1 per the MCP authorization spec.

## OAuth 2.1 — the moving parts

| Component | Role |
|---|---|
| Resource server | YOUR MCP server; verifies access tokens on every request |
| Authorization server | your IdP (Auth0, Stytch, Okta, Cognito, custom) |
| Client | ChatGPT on the user's behalf (CIMD, DCR, predefined clients, PKCE `S256`) |

### 1. Protected resource metadata (on your MCP server)

`GET https://your-mcp.example.com/.well-known/oauth-protected-resource` →
```json
{
  "resource": "https://your-mcp.example.com",
  "authorization_servers": ["https://auth.yourcompany.com"],
  "scopes_supported": ["items:read", "items:write"]
}
```
Unauthenticated block → `401` + header:
`WWW-Authenticate: Bearer resource_metadata="https://…/.well-known/oauth-protected-resource", scope="items:read"`

### 2. Authorization-server discovery metadata

`/.well-known/oauth-authorization-server` (or `openid-configuration`) must expose:
`authorization_endpoint`, `token_endpoint`,
`client_id_metadata_document_supported: true` (CIMD — preferred),
`token_endpoint_auth_methods_supported` (`none` | `private_key_jwt` for CIMD),
`registration_endpoint` (if DCR), `code_challenge_methods_supported: ["S256"]`.

### 3. Flow facts

- ChatGPT sends `resource=<your MCP URL>` on authorize + token requests; your IdP must
  copy it into the token audience (`aud`) so you can verify it was minted for you.
- Redirect URI to allowlist: `https://chatgpt.com/connector/oauth/{callback_id}`
  (legacy: `https://chatgpt.com/connector_platform_oauth_redirect`).
- CIMD: ChatGPT's `client_id` is an HTTPS metadata URL; `private_key_jwt` assertions
  verify against ChatGPT's published JWKS. DCR: one registration per connector instance.
- Optional `id_token_hint` support preserves login context on re-authorization.

### 4. Per-tool `securitySchemes`

Declare per tool (not server-wide):
- `{ "type": "noauth" }` — callable anonymously
- `{ "type": "oauth2", "scopes": [...] }` — needs a token
- Both together = anonymous works, linking unlocks more.

### 5. Trigger the linking UI (both halves required)

Metadata (`securitySchemes` + resource metadata) **AND** runtime challenge:
```json
{ "content": [{ "type": "text", "text": "Authentication required." }],
  "_meta": { "mcp/www_authenticate": [
    "Bearer resource_metadata=\"https://your-mcp.example.com/.well-known/oauth-protected-resource\", error=\"insufficient_scope\", error_description=\"You need to login to continue\"" ] },
  "isError": true }
```

### 6. Verify tokens yourself (every request)

JWKS signature + `iss` → `exp`/`nbf` → audience (`aud`/`resource`) → scopes → app policy.
Failure → `401` + `WWW-Authenticate` challenge. SDK helpers exist in both Python and
TypeScript MCP SDKs. ChatGPT does NOT support client-credentials/service accounts/custom
API keys.

### 7. Client identification (optional hardening)

ChatGPT presents an OpenAI-managed **mTLS client certificate** (leaf SAN
`mtls.prod.connectors.openai.com`, chains to OpenAI Connectors CA; don't pin the leaf).
You may also allowlist OpenAI's published egress IPs. mTLS authenticates the client;
OAuth still authenticates the user.

## Testing & rollout

- Dev tenant with short-lived tokens → MCP Inspector **Auth settings** to step through
  the OAuth flow → dogfood with trusted testers → plan revocation/refresh/scope changes.

## Deploy & connect

1. Dev: `ngrok http <port>` → HTTPS URL.
2. ChatGPT → Settings → Apps & Connectors → developer mode → create app with
   `https://…/mcp` URL. Test tools in real conversations.
3. Prod: low-latency HTTPS host (Cloudflare Workers, Fly.io, Vercel, AWS, Railway,
   Render…). Replace in-memory stores with a database. Version template URIs on deploy.

## Submission / directory review

- `_meta.ui.domain` set and unique per app (renders under
  `<domain>.web-sandbox.oaiusercontent.com`; enables fullscreen punch-out).
- CSP declared and minimal; `frameDomains` only if embedding is core (extra scrutiny,
  often rejected).
- `redirect_domains` under `openai/widgetCSP` for external flows via `openExternal`
  (skips safe-link modal, appends `redirectUrl` back to the conversation).
- Optional metadata: `openai/widgetDescription`, `openai/visibility: "private"` while
  testing, invoking/invoked status strings.
- Accurate tool annotations — review checks them; write tools get manual confirmation
  UX in ChatGPT.

## Security model (never skip)

- **Prompt injection**: any content reachable through tools (docs, emails, tickets) can
  carry hostile instructions. Trusting the developer ≠ trusting all content. Minimize
  access; keep sensitive-data apps narrow.
- **Write actions**: manual confirmation in-conversation; design idempotent; re-confirm
  destructive parameters in the current turn; observable side effects can be an
  exfiltration channel.
- **Excessive parameters** = privacy overreach (e.g., a read tool demanding
  `userAnnualIncome`). Only request fields the action needs.
- **No secrets** in `structuredContent`/`content`/`_meta`/widget state/tool JSON — all
  user-visible.
- Identity/authz only from verified tokens — never model args, memory, locale,
  `openai/userAgent`.
- Users should connect only to official/trusted servers; report malicious servers to
  security@openai.com.
