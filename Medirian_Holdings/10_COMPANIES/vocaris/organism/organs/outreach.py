"""Outreach organ: writes ready-to-send drafts to outbox/. It never sends anything.

House rule (CLAUDE.md #3): drafts go to outbox/; Ahmad presses send himself. After sending, record it with
`record <lead_id> contacted --channel <channel>` so the sequence and the brain can learn.

Channels: linkedin (DM), email, whatsapp (opt-in only), call_list (script for a phone call).
"""
from __future__ import annotations

import time
from datetime import datetime

from .. import ROOT, immune
from ..markets import Market
from .personalize import banned_phrases, personalize

OUTBOX = ROOT / "outbox"
CHANNELS = ["linkedin", "email", "whatsapp", "call_list"]
FIELDS = {"linkedin": ["linkedin"], "email": ["email_subject", "email_body"],
          "whatsapp": ["whatsapp"], "call_list": ["call_script"]}


def run(market: Market, channel: str, memory, limit: int = 5, min_score: float = 0,
        now: float | None = None) -> dict:
    """Draft messages for the best eligible leads on one channel. Returns a summary with per-lead verdicts."""
    if channel not in CHANNELS:
        raise ValueError(f"unknown channel {channel}")
    now = now or time.time()
    results = {"drafted": 0, "blocked": 0, "items": [], "files": []}
    lang = market.languages[0]
    day_dir = OUTBOX / market.id / datetime.fromtimestamp(now).strftime("%Y-%m-%d")

    for row in memory.leads(market=market.id, order_by_score=True):
        if results["drafted"] >= limit:
            break
        lead = dict(row)
        if (lead["score"] or 0) < min_score or not lead["demo_link"]:
            continue
        verdict = immune.check(lead, market, channel, memory, now=now)
        if not verdict:
            results["blocked"] += 1
            results["items"].append((lead["name"], "BLOCKED", verdict.reason))
            continue

        copy = personalize(lead, market)["copy"][lang]
        text = "\n\n".join(copy[f] for f in FIELDS[channel])
        bad = banned_phrases(text)
        if bad:   # a template edit slipped in an absolute claim — stop rather than embarrass Vocaris
            results["blocked"] += 1
            results["items"].append((lead["name"], "BLOCKED", f"banned phrase {bad}"))
            continue

        touch = len(immune.touches(lead["id"], memory)) + 1
        day_dir.mkdir(parents=True, exist_ok=True)
        path = day_dir / f"{lead['slug'] or lead['id'].replace(':', '_')}__{channel}.md"
        to = {"email": lead["email"], "linkedin": "(find the owner/manager on LinkedIn)",
              "whatsapp": lead["phone"], "call_list": lead["phone"]}[channel]
        note = "\n> ⚠️ لمسة ٤ أو ٥ بلا رد — غيّر الزاوية، لا تكرّر نفس الرسالة.\n" if touch >= 4 else ""
        path.write_text(
            f"# {lead['name']} — {channel} — لمسة {touch}/5\n\n"
            f"- **إلى:** {to}\n- **الرابط:** {lead['demo_link']}\n- **النقاط:** {lead['score']} ({lead['score_reasons']})\n"
            f"- **بعد الإرسال:** `python3 -m organism.cli record {lead['id']} contacted --channel {channel}`\n"
            f"{note}\n---\n\n{text}\n", encoding="utf-8")
        memory.record(market.id, "drafted", lead_id=lead["id"], channel=channel, ts=now)
        results["drafted"] += 1
        results["files"].append(str(path))
        results["items"].append((lead["name"], "DRAFTED", f"{channel} touch {touch}/5"))
    return results


def ads_plan(market: Market, memory) -> list[dict]:
    """Geo-targeting plan for paid ads: districts weighted by how many high-score leads they hold."""
    rows = memory.db.execute(
        "SELECT district, COUNT(*) n, AVG(score) s FROM leads WHERE market=? AND score>0 "
        "GROUP BY district ORDER BY n*s DESC", (market.id,)).fetchall()
    total = sum(r["n"] * (r["s"] or 0) for r in rows) or 1
    budget = market.channel("ads").get("daily_budget_usd", 0)
    return [{"district": r["district"], "leads": r["n"], "avg_score": round(r["s"] or 0, 1),
             "daily_budget_usd": round(budget * r["n"] * (r["s"] or 0) / total, 2)} for r in rows]
