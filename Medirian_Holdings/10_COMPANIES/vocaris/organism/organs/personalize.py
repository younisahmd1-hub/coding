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

# House rules (CLAUDE.md): no absolute claims ("every call answered", "guaranteed", "100%"), no invented numbers,
# one dialect per message (Gulf for the Gulf), lead angle = "the call you'll never know you lost".
TEMPLATES = {
    "en": {
        "email_subject": "{name}: your AI receptionist is ready — try it yourself",
        "email_body": (
            "Hi {name} team,\n\n"
            "A caller who doesn't get an answer rarely leaves a message — they call the next place. "
            "That's a booking you'll never know you lost.\n\n"
            "We've set up a Vocaris receptionist trained on {name}. It answers your phone 24/7 and books "
            "appointments directly.\n\n"
            "Call it now and hear it yourself: {demo_link}\n\n"
            "Offer: {trial}.\n\n"
            "— Ahmad, Vocaris\n\n"
            "Not for you? Reply \"no\" and we won't write again."
        ),
        "linkedin": (
            "Hi — I came across {name} and set up an AI receptionist trained on your business. It answers the "
            "phone and books appointments. Call it and hear it: {demo_link} ({trial}). If it's not for you, "
            "just say so and I won't message again."
        ),
        "whatsapp": (
            "Hi {name} 👋 We set up an AI receptionist trained on {name} — it answers your phone and books "
            "appointments. Call it here: {demo_link} ({trial}). Reply \"no\" to stop messages."
        ),
        "call_script": (
            "Hi, is this {name}? This is Ahmad from Vocaris. Quick question — when you're busy with a client "
            "and the phone rings, who picks up? [listen] We've set up an AI receptionist for {name} that answers "
            "the phone and books appointments. Can I send you the link so you can call it yourself? {trial}."
        ),
    },
    "ar": {
        "email_subject": "{name}: موظف استقبال جاهز باسمكم — جرّبوه بنفسكم",
        "email_body": (
            "هلا فريق {name}،\n\n"
            "الزبون اللي يتصل وما أحد يرد عليه، ما يترك رسالة — يتصل على اللي بعدكم. "
            "وهذي مكالمة ما راح تدرون أبد إنكم خسرتوها.\n\n"
            "جهّزنا موظف استقبال من Vocaris باسم {name}: يرد على تلفون المحل ٢٤ ساعة ويحجز المواعيد مباشرة.\n\n"
            "اتصلوا عليه الحين واسمعوه بنفسكم: {demo_link}\n\n"
            "العرض: {trial}.\n\n"
            "— أحمد، Vocaris\n\n"
            "إذا ما يناسبكم، ردّوا بكلمة «لا» وما راح نراسلكم مرة ثانية."
        ),
        "linkedin": (
            "هلا، شفت {name} وجهّزت لكم موظف استقبال بالذكاء الاصطناعي باسم المحل — يرد على التلفون ويحجز "
            "المواعيد. اتصلوا عليه واسمعوه: {demo_link} ({trial}). إذا ما يهمكم، قولوا لي وما أراسلكم مرة ثانية."
        ),
        "whatsapp": (
            "هلا {name} 👋 جهّزنا لكم موظف استقبال باسم المحل يرد على التلفون ويحجز المواعيد. "
            "اتصلوا عليه هني: {demo_link} ({trial}). إذا ما تبون رسايل، ردّوا بـ«لا»."
        ),
        "call_script": (
            "السلام عليكم، معي {name}؟ معك أحمد من Vocaris. سؤال سريع: يوم تكونون مشغولين مع زبون والتلفون "
            "يرن، منو يرد؟ [اسمع] جهّزنا لكم موظف استقبال باسم {name} يرد على التلفون ويحجز المواعيد. "
            "أقدر أرسل لكم الرابط تتصلون عليه وتسمعونه بنفسكم؟ {trial}."
        ),
    },
}

BANNED_PHRASES = ["every call", "100%", "guarantee", "كل مكالمة", "كل المكالمات", "مضمون", "١٠٠٪"]


def slugify(name: str, suffix: str = "") -> str:
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48] or "business"
    return f"{slug}-{suffix}" if suffix else slug


def personalize(lead: dict, market: Market) -> dict:
    suffix = lead["id"].split(":")[-1][-6:].lower()
    slug = slugify(lead["name"], suffix)
    demo_link = market.demo_link_template.format(slug=slug, market=market.id)
    copy = {}
    for lang in market.languages:
        if lang not in TEMPLATES:
            continue
        trial = market.offer.get(f"trial_{lang}") or market.offer.get("trial", "")
        ctx = {"name": lead["name"], "demo_link": demo_link, "trial": trial}
        copy[lang] = {k: v.format(**ctx) for k, v in TEMPLATES[lang].items()}
    return {"slug": slug, "demo_link": demo_link, "copy": copy}


def banned_phrases(text: str) -> list[str]:
    low = text.lower()
    return [p for p in BANNED_PHRASES if p.lower() in low]


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
