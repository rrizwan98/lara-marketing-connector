# Spec 02: Data Model

State store: SQLite (dev/demo) at `LARA_DB_PATH` (default `./lara.db`).
Production: identical surface backed by Neon/Postgres via `DATABASE_URL`.

All timestamps are UTC ISO-8601 strings. `*_md` columns hold Markdown. `data` holds JSON text.

## Tables

### users — one row per verified identity
| column | type | notes |
|--------|------|-------|
| `sub` | TEXT PK | verified subject (OAuth `sub`; demo: `public-demo`) |
| `email` | TEXT | from sign-in |
| `tier` | TEXT | `free` \| `pro` \| `max` (default `free`) |
| `created_at` | TEXT | |

### user_state — misc per-user preferences
| `sub` | TEXT PK (FK users) |
| `data` | TEXT (JSON) |

### clients — per-user marketing clients (the product-marketing foundation)
| `id` | INTEGER PK AUTOINCREMENT |
| `owner_sub` | TEXT (FK users) |
| `name` | TEXT |
| `context_md` | TEXT — the product-marketing context document |
| `created_at` | TEXT |
| UNIQUE(`owner_sub`, `name`) |

### deliverables — per-client history / notes (the "previous conversation" memory)
| `id` | INTEGER PK |
| `owner_sub` | TEXT |
| `client` | TEXT |
| `note` | TEXT |
| `created_at` | TEXT |

### usage — daily task counter (tier limits)
| `sub` | TEXT | PK part |
| `day` | TEXT (YYYY-MM-DD) | PK part |
| `count` | INTEGER | |

## Identity rule
Every write/read is keyed by the **verified `sub`** taken from the session token — never from a
tool argument. A user can only see/modify their own clients, deliverables, and state.

## db.py function surface
```
init_db()
get_or_create_user(sub, email) -> user
get_user(sub) -> user | None
set_tier(sub, tier)
get_state(sub) -> dict ; save_state(sub, dict)
list_clients(sub) -> [name] ; count_clients(sub) -> int
get_client_context(sub, name) -> md | None
save_client_context(sub, name, md)
list_deliverables(sub, client, since_days=None) -> [ {note, created_at} ]
log_deliverable(sub, client, note)
incr_usage(sub) -> new_count_today ; get_usage_today(sub) -> int
```
