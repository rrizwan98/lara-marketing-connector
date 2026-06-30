# Spec 05: Subscription Tiers (free / pro / max)

Built in **now**, enforced **later**. Controlled by one flag.

## Flags (env)
- `GATING_ENABLED` (default `false`): when false → everyone gets full access (public phase),
  limits ignored, all skills allowed. When true → enforce the matrix below by `users.tier`.
- `PUBLIC_TIER` (default `max`): the effective tier reported when gating is off.

## Matrix (proposal — tune freely)
| Capability | free | pro | max |
|---|---|---|---|
| Skills available | core set (10) | all 45 | all 45 (+ future premium tools) |
| Saved clients (`max_clients`) | 1 | 10 | unlimited (`-1`) |
| Tasks / day (`tasks_per_day`) | 10 | 200 | unlimited (`-1`) |
| History retention (`history_days`) | 7 | 90 | unlimited (`-1`) |
| Real domain tools (future) | ✗ | limited | full |
| Router map | basic | full | full + custom |

### `free` core skills (10)
`product-marketing, copywriting, social, emails, content-strategy, seo-audit, cro, offers,
customer-research, marketing-ideas`

## Enforcement points (single helper `gate()` in server.py)
- `domain_get_skill`: skill ∈ allowed-for-tier else `forbidden`.
- `domain_get_skill`: `get_usage_today < tasks_per_day` else `limit_reached`.
- `user_save_client_context`: new client only if `count_clients < max_clients` else `limit_reached`.
- `user_get_history`: filter `created_at >= now - history_days`.
- When `GATING_ENABLED=false`: all checks pass, tier reported as `PUBLIC_TIER`.

## Future: turning subscriptions on (no re-architecture)
1. Wire OAuth (`06-auth.md`) so each user is a real `sub`.
2. Add billing (e.g., Stripe) → on purchase call `db.set_tier(sub, tier)`.
3. Set `GATING_ENABLED=true`.
That's it — tables (`tier`, `usage`) and the `gate()` helper already exist.
