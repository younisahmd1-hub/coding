"""Personalization organ: gives every lead its own demo link and outreach copy.

The zero-friction personalized link is Vocaris's main edge; this makes it happen at scale.
"""
from __future__ import annotations

import os
import re
import unicodedata

import requests

from ..markets import Market

API_BASE = os.environ.get("VOCARIS_API_BASE", "https://api.vocaris.ai/v4/p-ebc232c6/voxibook/api/v1")

TEMPLATES = {
    "en": {
        "email_subject": "{name}: we set up your AI receptionist (free)",
        "email_body": (
            "Hi {name} team,\n\n"
            "When you're busy with a client, calls to your salon go unanswered — and most callers book "
            "somewhere else instead of calling back.\n\n"
            "We've already built a Vocaris receptionist trained on {name}. It answers every call 24/7 "
            "and books straight into your calendar.\n\n"
            "Your page is ready, no forms and no card: {demo_link}\n\n"
            "Offer: {trial}.\n\n"
            "— Vocaris\n\n"
            "Not interested? Reply STOP and we won't contact you again."
        ),
        "whatsapp": (
            "Hi {name} 👋 We built an AI receptionist trained on {name} — it answers every call 24/7 and books "
            "into your calendar. Try it here: {demo_link} ({trial}). Reply STOP to opt out."
        ),
        "call_script": (
            "Hi, is this {name}? I'm calling from Vocaris. Quick question — when you're with a client and the "
            "phone rings, who answers it? [listen] We've already built an AI receptionist set up for {name}; "
            "it answers 24/7 and books into your calendar. Can I send you the link on WhatsApp? It's {trial}."
        ),
    },
    "ar": {
        "email_subject": "{name}: جهّزنا لكم موظف استقبال ذكي (مجاناً)",
        "email_body": (
            "مرحباً فريق {name}،\n\n"
            "لما تكونون مشغولين مع زبون، المكالمات تضيع — وأغلب المتصلين يحجزون عند غيركم بدل ما يعيدون الاتصال.\n\n"
            "جهّزنا لكم موظف استقبال Vocaris مدرَّب على {name}. يرد على كل مكالمة ٢٤/٧ "
            "ويحجز مباشرة في التقويم.\n\n"
            "صفحتكم جاهزة، بدون نماذج وبدون بطاقة: {demo_link}\n\n"
            "العرض: {trial}.\n\n"
            "— Vocaris\n\n"
            "ما يهمكم؟ ردّوا بكلمة STOP وما راح نتواصل معكم مرة ثانية."
        ),
        "whatsapp": (
            "هلا {name} 👋 موظف الاستقبال الذكي من Vocaris جاهز لكم — يرد على كل مكالمة ٢٤/٧ ويحجز في التقويم. "
            "شوفوه هنا: {demo_link} ({trial}). للإلغاء أرسلوا STOP."
        ),
        "call_script": (
            "مرحبا، معي {name}؟ أنا من Vocaris. سؤال سريع — لما تكون مع زبون والتلفون يرن، مين يرد؟ [استمع] "
            "جهّزنا موظف استقبال ذكي خاص فيكم يرد ٢٤/٧ ويحجز في التقويم. أقدر أرسل لك الرابط على واتساب؟ {trial}."
        ),
    },
}


def slugify(name: str, suffix: str = "") -> str:
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48] or "business"
    return f"{slug}-{suffix}" if suffix else slug


def personalize(lead: dict, market: Market) -> dict:
    suffix = lead["id"].split(":")[-1][-6:].lower()
    slug = slugify(lead["name"], suffix)
    demo_link = market.demo_link_template.format(slug=slug, market=market.id)
    ctx = {"name": lead["name"], "demo_link": demo_link, "trial": market.offer.get("trial", "free trial")}
    copy = {lang: {k: v.format(**ctx) for k, v in TEMPLATES[lang].items()}
            for lang in market.languages if lang in TEMPLATES}
    return {"slug": slug, "demo_link": demo_link, "copy": copy}


def demo_page_live(slug: str, session=requests) -> bool:
    """True if the Vocaris backend has a demo for this slug (public endpoint, no auth)."""
    try:
        r = session.get(f"{API_BASE}/public/outreach/demo/{slug}", timeout=15)
        return r.status_code == 200
    except Exception:
        return False


def verify_market(market: Market, memory, session=requests) -> dict:
    stats = {"checked": 0, "live": 0}
    for row in memory.leads(market=market.id):
        if not row["slug"] or row["demo_verified"]:
            continue
        stats["checked"] += 1
        if demo_page_live(row["slug"], session):
            memory.update_lead(row["id"], demo_verified=1)
            stats["live"] += 1
    return stats


def personalize_market(market: Market, memory, min_score: float = 0) -> int:
    n = 0
    for row in memory.leads(market=market.id, stage="scored"):
        if (row["score"] or 0) < min_score or row["demo_link"]:
            continue
        p = personalize(dict(row), market)
        memory.update_lead(row["id"], slug=p["slug"], demo_link=p["demo_link"])
        n += 1
    return n
