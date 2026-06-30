"""
config_store.py — Lara's brain (data, not logic).

Holds the persona, the non-negotiable rules, the task->skill router map, the skill
categories, and the subscription tier definitions. server.py imports these and
serves them through begin_session() and the gate() helper.

See specs/03-session-contract.md and specs/05-tiers.md.
"""

from __future__ import annotations

# --------------------------------------------------------------------------- #
# Persona & rules (returned by begin_session / config_get_*)
# --------------------------------------------------------------------------- #

PERSONA = (
    "You are Lara, a senior Digital Marketing specialist and employee at Canz Marketing. "
    "You are female, warm, confident, and impeccably polite. You always use respectful 'aap'. "
    "In Urdu/Roman Urdu you ALWAYS use feminine verb forms (kar deti hoon, bana deti hoon, "
    "bata deti hoon). You mirror the client's language: Roman Urdu -> easy Roman Urdu, "
    "English -> English, mixed -> match them. You know the current date/time (Asia/Karachi) "
    "and this client's history, so clients never have to repeat themselves. You produce "
    "complete, usable marketing work, not vague advice."
)

MANDATORY_RULES = [
    "SKILLS ARE MANDATORY: for ANY marketing task, first choose the right skill from the "
    "router_map (or call domain_route_task), then call domain_get_skill(name) and FOLLOW it. "
    "Never produce marketing work from general memory.",
    "FOUNDATION FIRST: before real work for a client, load or build their product-marketing "
    "context via user_get_client_context / user_save_client_context. Never invent a client's "
    "product, audience, prices, or results — ask or mark 'TODO: confirm'.",
    "CONFIDENTIALITY: never mix or reveal one client's data inside another client's work.",
    "STAY IN ROLE: you do digital marketing. Politely steer off-topic requests back. Be polite "
    "even with rude messages.",
    "LOG YOUR WORK: after a meaningful deliverable, call user_log_deliverable(client, note).",
]

FAIL_CLOSED = (
    "If begin_session is unavailable or any tool returns ok=false, tell the user the session "
    "can't continue right now and stop. Do NOT improvise or fabricate an answer."
)

# --------------------------------------------------------------------------- #
# Skill categories (for a tidy catalog)
# --------------------------------------------------------------------------- #

CATEGORY_MAP = {
    "Strategy & GTM": [
        "product-marketing", "marketing-plan", "marketing-ideas", "marketing-psychology",
        "content-strategy", "customer-research", "competitor-profiling", "offers", "pricing",
        "launch",
    ],
    "Content & Copy": [
        "copywriting", "copy-editing", "social", "emails", "cold-email", "sms", "image", "video",
    ],
    "SEO & Discovery": [
        "seo-audit", "ai-seo", "programmatic-seo", "site-architecture", "competitors", "schema",
        "aso",
    ],
    "Conversion (CRO)": ["cro", "signup", "onboarding", "popups", "paywalls"],
    "Paid & Measurement": ["ads", "ad-creative", "analytics", "ab-testing"],
    "Growth & Retention": [
        "referrals", "lead-magnets", "free-tools", "co-marketing", "community-marketing",
        "churn-prevention",
    ],
    "Sales & RevOps": [
        "revops", "sales-enablement", "prospecting", "public-relations", "directory-submissions",
    ],
}


def category_of(skill: str) -> str:
    for cat, skills in CATEGORY_MAP.items():
        if skill in skills:
            return cat
    return "Other"


# --------------------------------------------------------------------------- #
# Router map: free-text task -> skill name (the "which skill, when" logic)
# --------------------------------------------------------------------------- #

ROUTER_MAP = {
    # Strategy / foundation
    "set up product or audience context": "product-marketing",
    "positioning or ICP or target audience": "product-marketing",
    "full marketing plan for a client": "marketing-plan",
    "need marketing ideas or inspiration": "marketing-ideas",
    "apply psychology or behavioral science": "marketing-psychology",
    "plan a content strategy or topics": "content-strategy",
    "run or synthesize customer research": "customer-research",
    "research or profile competitors": "competitor-profiling",
    "design or improve an offer": "offers",
    "pricing or packaging or monetization": "pricing",
    "plan a product launch or announcement": "launch",
    # Content & copy
    "homepage or landing or website copy": "copywriting",
    "write or rewrite marketing copy": "copywriting",
    "edit or polish existing copy": "copy-editing",
    "social media posts or strategy": "social",
    "email sequence or drip or lifecycle": "emails",
    "cold outreach email or B2B follow-up": "cold-email",
    "sms or mms marketing flow": "sms",
    "create or optimize marketing images": "image",
    "produce video content": "video",
    # SEO & discovery
    "seo audit or diagnose seo issues": "seo-audit",
    "optimize for AI search or get cited by LLMs": "ai-seo",
    "scaled or programmatic seo pages": "programmatic-seo",
    "site architecture or navigation or url structure": "site-architecture",
    "comparison or alternative pages": "competitors",
    "schema markup or structured data": "schema",
    "app store or play store listing": "aso",
    # CRO
    "improve conversions on a page or form": "cro",
    "signup or registration or trial flow": "signup",
    "onboarding or activation or time-to-value": "onboarding",
    "popups or modals or overlays": "popups",
    "in-app paywall or upgrade screen": "paywalls",
    # Paid & measurement
    "paid ads campaign (google meta linkedin)": "ads",
    "bulk ad creative or headlines": "ad-creative",
    "analytics or tracking setup": "analytics",
    "a/b test or experiment": "ab-testing",
    # Growth & retention
    "referral or affiliate program": "referrals",
    "lead magnet for email capture": "lead-magnets",
    "free tool or calculator for marketing": "free-tools",
    "co-marketing or partner campaign": "co-marketing",
    "build or leverage a community": "community-marketing",
    "reduce churn or save offers or dunning": "churn-prevention",
    # Sales & revops
    "revenue operations or lead lifecycle": "revops",
    "sales decks or one-pagers or objection docs": "sales-enablement",
    "find or qualify prospects": "prospecting",
    "PR or press or journalist outreach": "public-relations",
    "submit product to directories": "directory-submissions",
}

ALL_SKILLS = sorted({s for skills in CATEGORY_MAP.values() for s in skills})

# --------------------------------------------------------------------------- #
# Tiers (specs/05-tiers.md). -1 means unlimited.
# --------------------------------------------------------------------------- #

FREE_SKILLS = [
    "product-marketing", "copywriting", "social", "emails", "content-strategy",
    "seo-audit", "cro", "offers", "customer-research", "marketing-ideas",
]

TIERS = {
    "free": {"skills": FREE_SKILLS, "max_clients": 1, "tasks_per_day": 10, "history_days": 7},
    "pro": {"skills": "all", "max_clients": 10, "tasks_per_day": 200, "history_days": 90},
    "max": {"skills": "all", "max_clients": -1, "tasks_per_day": -1, "history_days": -1},
}


def tier_def(tier: str) -> dict:
    return TIERS.get(tier, TIERS["free"])


def skills_for_tier(tier: str) -> list[str]:
    allowed = tier_def(tier)["skills"]
    return ALL_SKILLS if allowed == "all" else list(allowed)


def is_skill_allowed(tier: str, name: str) -> bool:
    allowed = tier_def(tier)["skills"]
    return True if allowed == "all" else name in allowed


def limits_for_tier(tier: str) -> dict:
    d = tier_def(tier)
    return {
        "max_clients": d["max_clients"],
        "tasks_per_day": d["tasks_per_day"],
        "history_days": d["history_days"],
    }
