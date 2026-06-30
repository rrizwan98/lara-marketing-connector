"""
skills_repo.py — read the bundled marketing skills from skills/<name>/SKILL.md.

Provides the catalog (name + description + category) and one skill's full body.
get_skill_body is path-safe: a name must match a known skill folder.

See specs/04-tools.md.
"""

from __future__ import annotations

import os
import re

import yaml

import config_store

SKILLS_DIR = os.environ.get(
    "LARA_SKILLS_DIR", os.path.join(os.path.dirname(__file__), "skills")
)

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
_catalog_cache: list[dict] | None = None
_names_cache: set[str] | None = None


def _parse_frontmatter(text: str) -> dict:
    """Extract the YAML frontmatter block (--- ... ---) at the top of a SKILL.md."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    block = text[3:end].strip()
    try:
        data = yaml.safe_load(block)
        return data if isinstance(data, dict) else {}
    except yaml.YAMLError:
        return {}


def _skill_dirs() -> list[str]:
    if not os.path.isdir(SKILLS_DIR):
        return []
    out = []
    for entry in sorted(os.listdir(SKILLS_DIR)):
        d = os.path.join(SKILLS_DIR, entry)
        if os.path.isdir(d) and os.path.isfile(os.path.join(d, "SKILL.md")):
            out.append(entry)
    return out


def _build_catalog() -> list[dict]:
    catalog = []
    for name in _skill_dirs():
        path = os.path.join(SKILLS_DIR, name, "SKILL.md")
        try:
            with open(path, "r", encoding="utf-8") as fh:
                fm = _parse_frontmatter(fh.read())
        except OSError:
            fm = {}
        desc = (fm.get("description") or "").strip()
        if len(desc) > 280:
            desc = desc[:277] + "..."
        catalog.append(
            {
                "name": fm.get("name", name),
                "folder": name,
                "description": desc,
                "category": config_store.category_of(name),
            }
        )
    return catalog


def get_catalog() -> list[dict]:
    global _catalog_cache, _names_cache
    if _catalog_cache is None:
        _catalog_cache = _build_catalog()
        _names_cache = {c["folder"] for c in _catalog_cache}
    return _catalog_cache


def valid_skill(name: str) -> bool:
    get_catalog()
    return bool(name) and _NAME_RE.match(name) is not None and name in (_names_cache or set())


def get_skill_body(name: str) -> str | None:
    """Return the full SKILL.md body for a known skill, or None. Path-traversal safe."""
    if not valid_skill(name):
        return None
    path = os.path.join(SKILLS_DIR, name, "SKILL.md")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return None


def count() -> int:
    return len(get_catalog())
