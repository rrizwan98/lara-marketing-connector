# Lara Marketing Connector — Spec 00: Overview

## What this is
A **remote MCP server** (a "connector" in the AgentFactory book sense) whose customer is an AI.
It carries **Lara's full marketing brain** so any MCP-capable host (Claude Code, Codex,
OpenCode, OpenClaw, claude.ai) can connect to one URL and get the complete digital-marketing
employee.

## What it contains
1. **45 marketing skills** (served as tool results, on demand).
2. **The orchestration logic** — "which skill, when" — delivered via `begin_session()` so the
   logic travels with the skills (this is the part a bare skills-folder loses).
3. **Persona + rules** (polite female marketer, mandatory-skill discipline, language mirroring).
4. **Per-client context + history** (the product-marketing foundation, remembered per user).

## Guiding principle (the book)
> "You own the server, not the mind that calls it."
We expose **tools**; the AI decides which to call. We never trust the model for identity or
truth — only for orchestration.

## Scope
- **v0.1 (now): PUBLIC.** Runs in demo identity mode (no per-user sign-in yet). Everyone gets
  full access. Goal: get Lara reachable from any host by URL.
- **Future: SUBSCRIPTION.** Tiers `free` / `pro` / `max`. The data model and gating machinery
  are built in now (a flag flip + billing later — no re-architecture). See `05-tiers.md`.

## Non-goals (v0.1)
- Real third-party tool calls (CRM, ad APIs, image-gen) — these are future `domain_*` tools.
- Production OAuth wiring is **specced** (`06-auth.md`) with a clean seam, but the default run
  is demo mode.
- Billing/payments.

## Success test
From a fresh host: add the connector URL → call `begin_session()` → receive persona + rules +
router map + skills → call `domain_get_skill("copywriting")` → produce on-brand copy. No host
ever needs the skills installed locally.
