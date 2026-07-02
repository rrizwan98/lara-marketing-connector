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

# NOTE: kept for potential future use; NOT used by routing (user chose to keep
# original router behavior — UI-only changes).
_UNUSED_SKILL_KEYWORDS: dict[str, dict[str, int]] = {
    "product-marketing": {"positioning": 4, "icp": 4, "audience": 2, "persona": 2,
                          "target market": 3, "product context": 4},
    "marketing-plan": {"marketing plan": 4, "plan": 2, "roadmap": 2, "budget": 2, "strategy": 2},
    "marketing-ideas": {"idea": 3, "inspiration": 3, "brainstorm": 3},
    "marketing-psychology": {"psychology": 4, "persuasion": 3, "bias": 2, "behavioral": 3},
    "content-strategy": {"content strategy": 4, "content": 2, "topic": 2, "blog": 2,
                         "editorial": 3, "content calendar": 4},
    "customer-research": {"research": 2, "interview": 3, "survey": 3, "feedback": 2,
                          "voice of customer": 4},
    "competitor-profiling": {"competitor": 4, "rival": 3, "benchmark": 2},
    "offers": {"offer": 4, "bundle": 3, "guarantee": 3, "value proposition": 3},
    "pricing": {"pricing": 4, "price": 3, "packaging": 3, "monetization": 3, "tier": 2},
    "launch": {"launch": 4, "release": 2, "announcement": 3, "go to market": 3},
    "copywriting": {"copy": 3, "headline": 3, "homepage": 3, "landing page": 4,
                    "landing": 2, "website copy": 4, "hero": 2, "tagline": 3},
    "copy-editing": {"edit": 3, "polish": 3, "rewrite": 3, "proofread": 4, "refresh": 2},
    "social": {"social": 3, "instagram": 4, "linkedin": 4, "twitter": 4, "facebook": 3,
               "tiktok": 4, "post": 2, "caption": 3},
    "emails": {"email": 3, "newsletter": 4, "drip": 4, "sequence": 3, "lifecycle": 3,
               "welcome flow": 4, "welcome sequence": 4},
    "cold-email": {"cold email": 4, "cold outreach": 4, "outreach": 3},
    "sms": {"sms": 4, "text message": 4, "mms": 4},
    "image": {"image": 3, "graphic": 3, "banner": 2, "visual": 2, "photo": 2},
    "video": {"video": 4, "reel": 3, "youtube": 3, "short-form": 3},
    "seo-audit": {"seo": 3, "ranking": 3, "google search": 3, "organic traffic": 4,
                  "seo audit": 4},
    "ai-seo": {"ai search": 4, "llm": 3, "cited": 3, "aeo": 4, "geo": 3, "chatgpt search": 4},
    "programmatic-seo": {"programmatic": 4, "pages at scale": 4, "template pages": 3},
    "site-architecture": {"architecture": 3, "navigation": 3, "sitemap": 4, "url structure": 4},
    "competitors": {"comparison": 3, "alternative": 3, "versus": 3, "vs page": 4},
    "schema": {"schema": 4, "structured data": 4, "markup": 3, "rich snippet": 4},
    "aso": {"app store": 4, "play store": 4, "aso": 4, "app listing": 4},
    "cro": {"conversion": 3, "convert": 3, "booking": 3, "book": 2, "checkout": 3,
            "cart": 3, "abandon": 3, "not converting": 4, "optimize page": 3},
    "signup": {"signup flow": 4, "registration": 4, "register": 3, "trial": 3,
               "sign up": 2, "signup": 2},
    "onboarding": {"onboarding": 4, "activation": 4, "first-run": 4, "time to value": 4},
    "popups": {"popup": 4, "modal": 3, "overlay": 3, "exit intent": 4},
    "paywalls": {"paywall": 4, "upgrade screen": 4, "upsell": 3, "premium": 2},
    "ads": {"ads": 3, "ad campaign": 4, "google ads": 4, "meta ads": 4, "ppc": 4,
            "paid": 3, "campaign": 2, "advertising": 3},
    "ad-creative": {"ad creative": 4, "ad copy": 4, "ad variation": 4, "creative": 2},
    "analytics": {"analytics": 4, "tracking": 3, "ga4": 4, "event": 2, "attribution": 4,
                  "measure": 2},
    "ab-testing": {"a/b test": 4, "ab test": 4, "experiment": 3, "variant": 3, "split test": 4},
    "referrals": {"referral": 4, "affiliate": 4, "word of mouth": 4, "invite": 2},
    "lead-magnets": {"lead magnet": 4, "ebook": 3, "freebie": 3, "email capture": 4},
    "free-tools": {"calculator": 4, "free tool": 4},
    "co-marketing": {"partner": 3, "partnership": 4, "collab": 3, "joint campaign": 4},
    "community-marketing": {"community": 4, "forum": 3, "members": 2},
    "churn-prevention": {"churn": 4, "cancel": 4, "cancellation": 4, "retention": 4,
                         "retain": 3, "dunning": 4, "winback": 4, "win back": 4,
                         "failed payment": 4, "stop using": 3, "drop off": 3},
    "revops": {"revops": 4, "lead scoring": 4, "routing": 3, "pipeline": 3, "crm": 3,
               "lifecycle stages": 4},
    "sales-enablement": {"deck": 3, "pitch": 3, "one-pager": 4, "objection": 4,
                         "demo script": 4, "sales collateral": 4},
    "prospecting": {"prospect": 4, "lead list": 4, "qualify": 3},
    "public-relations": {"pr": 3, "press": 4, "journalist": 4, "media coverage": 4},
    "directory-submissions": {"directory": 4, "submit": 2, "listing": 2, "product hunt": 4},
}

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
