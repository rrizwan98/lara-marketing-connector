"""
db.py — state store (SQLite for dev/demo; same surface for Neon/Postgres in prod).

Keyed strictly by the verified `sub` from the session token. See specs/02-data-model.md.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone, timedelta

DB_PATH = os.environ.get("LARA_DB_PATH", os.path.join(os.path.dirname(__file__), "lara.db"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    with _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                sub TEXT PRIMARY KEY,
                email TEXT,
                tier TEXT NOT NULL DEFAULT 'free',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS user_state (
                sub TEXT PRIMARY KEY,
                data TEXT NOT NULL DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_sub TEXT NOT NULL,
                name TEXT NOT NULL,
                context_md TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                UNIQUE(owner_sub, name)
            );
            CREATE TABLE IF NOT EXISTS deliverables (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_sub TEXT NOT NULL,
                client TEXT NOT NULL,
                note TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS usage (
                sub TEXT NOT NULL,
                day TEXT NOT NULL,
                count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (sub, day)
            );
            """
        )


# --------------------------------------------------------------------------- #
# users
# --------------------------------------------------------------------------- #

def get_or_create_user(sub: str, email: str) -> dict:
    with _conn() as c:
        row = c.execute("SELECT * FROM users WHERE sub = ?", (sub,)).fetchone()
        if row is None:
            c.execute(
                "INSERT INTO users (sub, email, tier, created_at) VALUES (?, ?, 'free', ?)",
                (sub, email, _now()),
            )
            row = c.execute("SELECT * FROM users WHERE sub = ?", (sub,)).fetchone()
        elif email and row["email"] != email:
            c.execute("UPDATE users SET email = ? WHERE sub = ?", (email, sub))
            row = c.execute("SELECT * FROM users WHERE sub = ?", (sub,)).fetchone()
        return dict(row)


def get_user(sub: str) -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT * FROM users WHERE sub = ?", (sub,)).fetchone()
        return dict(row) if row else None


def set_tier(sub: str, tier: str) -> None:
    with _conn() as c:
        c.execute("UPDATE users SET tier = ? WHERE sub = ?", (tier, sub))


# --------------------------------------------------------------------------- #
# user_state
# --------------------------------------------------------------------------- #

def get_state(sub: str) -> dict:
    with _conn() as c:
        row = c.execute("SELECT data FROM user_state WHERE sub = ?", (sub,)).fetchone()
        return json.loads(row["data"]) if row else {}


def save_state(sub: str, data: dict) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO user_state (sub, data) VALUES (?, ?) "
            "ON CONFLICT(sub) DO UPDATE SET data = excluded.data",
            (sub, json.dumps(data)),
        )


# --------------------------------------------------------------------------- #
# clients (product-marketing context)
# --------------------------------------------------------------------------- #

def list_clients(sub: str) -> list[str]:
    with _conn() as c:
        rows = c.execute(
            "SELECT name FROM clients WHERE owner_sub = ? ORDER BY name", (sub,)
        ).fetchall()
        return [r["name"] for r in rows]


def count_clients(sub: str) -> int:
    with _conn() as c:
        return c.execute(
            "SELECT COUNT(*) AS n FROM clients WHERE owner_sub = ?", (sub,)
        ).fetchone()["n"]


def get_client_context(sub: str, name: str) -> str | None:
    with _conn() as c:
        row = c.execute(
            "SELECT context_md FROM clients WHERE owner_sub = ? AND name = ?", (sub, name)
        ).fetchone()
        return row["context_md"] if row else None


def client_exists(sub: str, name: str) -> bool:
    with _conn() as c:
        return (
            c.execute(
                "SELECT 1 FROM clients WHERE owner_sub = ? AND name = ?", (sub, name)
            ).fetchone()
            is not None
        )


def save_client_context(sub: str, name: str, context_md: str) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO clients (owner_sub, name, context_md, created_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(owner_sub, name) DO UPDATE SET context_md = excluded.context_md",
            (sub, name, context_md, _now()),
        )


# --------------------------------------------------------------------------- #
# deliverables (history)
# --------------------------------------------------------------------------- #

def log_deliverable(sub: str, client: str, note: str) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO deliverables (owner_sub, client, note, created_at) VALUES (?, ?, ?, ?)",
            (sub, client, note, _now()),
        )


def list_deliverables(sub: str, client: str, limit: int = 10, since_days: int | None = None) -> list[dict]:
    query = "SELECT note, created_at FROM deliverables WHERE owner_sub = ? AND client = ?"
    params: list = [sub, client]
    if since_days is not None and since_days >= 0:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=since_days)).isoformat()
        query += " AND created_at >= ?"
        params.append(cutoff)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with _conn() as c:
        rows = c.execute(query, params).fetchall()
        return [dict(r) for r in rows]


# --------------------------------------------------------------------------- #
# usage (daily task counter)
# --------------------------------------------------------------------------- #

def incr_usage(sub: str) -> int:
    day = _today()
    with _conn() as c:
        c.execute(
            "INSERT INTO usage (sub, day, count) VALUES (?, ?, 1) "
            "ON CONFLICT(sub, day) DO UPDATE SET count = count + 1",
            (sub, day),
        )
        return c.execute(
            "SELECT count FROM usage WHERE sub = ? AND day = ?", (sub, day)
        ).fetchone()["count"]


def get_usage_today(sub: str) -> int:
    with _conn() as c:
        row = c.execute(
            "SELECT count FROM usage WHERE sub = ? AND day = ?", (sub, _today())
        ).fetchone()
        return row["count"] if row else 0
