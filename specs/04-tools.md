# Spec 04: Tool Contracts

Groups: `config_*` (brain), `domain_*` (skills + future real tools), `user_*` (context/state).
Every tool except `health` and `begin_session` requires a valid `session_token`.
All tools return either their documented payload or a fail-closed error object (see 03).

## Open (no session)
### `health() -> {ok, name, version, gating_enabled}`
Liveness. No identity, no state.

### `begin_session() -> SessionContract`
See `03-session-contract.md`. Resolves principal, mints token, returns the brain.

## config_* (brain)
### `config_get_persona(session_token) -> {persona}`
### `config_get_rules(session_token) -> {mandatory_rules, fail_closed}`
(begin_session already returns these; these exist for re-fetch mid-session.)

## domain_* (skills now; real tools later)
### `domain_list_skills(session_token) -> {skills: [{name, description, category, allowed}]}`
Full catalog from `skills/`. `allowed` reflects tier (when gating on).

### `domain_get_skill(session_token, name) -> {name, body} | error`
Returns the full `SKILL.md` body. **Path-safe**: `name` must match a known skill folder.
Tier-gated: a `free` user requesting a non-free skill → `forbidden` (when gating on).
Counts as one task (usage++).

### `domain_route_task(session_token, task) -> {skills: [name], rationale}`
Maps a free-text task to the best skill(s) using the router map + keyword match.
Does not consume a task quota (cheap helper).

## user_* (per-user, keyed by token sub)
### `user_get_profile(session_token) -> {email, tier, clients_count, limits}`
### `user_list_clients(session_token) -> {clients: [name]}`
### `user_get_client_context(session_token, client) -> {client, context_md|null}`
### `user_save_client_context(session_token, client, context_md) -> {ok} | error`
Create/update the product-marketing context. Tier-gated by `max_clients` (new client over the
limit → `limit_reached` when gating on).
### `user_get_history(session_token, client, limit=10) -> {deliverables: [{note, created_at}]}`
Honors `history_days` retention by tier (when gating on).
### `user_log_deliverable(session_token, client, note) -> {ok}`

## Error model
`{ ok:false, error, message }` with `error` in
`{session_required, session_invalid, unavailable, limit_reached, forbidden, not_found, bad_input}`.

## Invariants enforced per tool
- No tool accepts an identity argument.
- Every stateful tool derives `sub` + `tier` from `verify(session_token)`.
- `domain_get_skill` validates `name` against the real folder set (no traversal).
- Gating is centralized in one helper so `free/pro/max` behavior is consistent.
