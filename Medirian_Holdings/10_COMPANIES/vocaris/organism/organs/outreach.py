"""Outreach organ: delivers personalized messages through each channel, only after the immune system says yes.

Everything runs in DRY RUN unless `live=True` and the channel's credentials are configured.
  * email     — SMTP (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM)
  * whatsapp  — WhatsApp Cloud API approved template (WA_TOKEN, WA_PHONE_NUMBER_ID, WA_TEMPLATE)
  * call_list — writes a CSV for a human caller with the script per lead
"""
from __future__ import annotations

import csv
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

import requests

from .. import DATA_DIR, immune
from ..markets import Market
from .personalize import personalize


def _send_email(to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = os.environ["SMTP_FROM"]
    msg["To"] = to
    msg["Subject"] = subject
    msg["List-Unsubscribe"] = f"<mailto:{os.environ['SMTP_FROM']}?subject=STOP>"
    msg.set_content(body)
    with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", 587))) as s:
        s.starttls()
        s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        s.send_message(msg)


def _send_whatsapp(phone: str, name: str, demo_link: str) -> None:
    # Business-initiated WhatsApp must use a Meta-approved template; params: {{1}} name, {{2}} link.
    url = f"https://graph.facebook.com/v21.0/{os.environ['WA_PHONE_NUMBER_ID']}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": "".join(ch for ch in phone if ch.isdigit()),
        "type": "template",
        "template": {
            "name": os.environ["WA_TEMPLATE"],
            "language": {"code": os.environ.get("WA_TEMPLATE_LANG", "en")},
            "components": [{"type": "body", "parameters": [
                {"type": "text", "text": name}, {"type": "text", "text": demo_link}]}],
        },
    }
    r = requests.post(url, json=payload, headers={"Authorization": f"Bearer {os.environ['WA_TOKEN']}"}, timeout=30)
    r.raise_for_status()


def run(market: Market, channel: str, memory, limit: int = 20, live: bool = False,
        min_score: float = 0) -> dict:
    """Contact the best-scored eligible leads on one channel. Returns a summary with per-lead verdicts."""
    results = {"sent": 0, "blocked": 0, "dry_run": not live, "items": [], "file": None}
    call_rows = []
    lang = market.languages[0]

    for row in memory.leads(market=market.id, order_by_score=True):
        if results["sent"] >= limit:
            break
        lead = dict(row)
        if (lead["score"] or 0) < min_score or not lead["demo_link"]:
            continue
        verdict = immune.check(lead, market, channel, memory)
        if not verdict:
            results["blocked"] += 1
            results["items"].append((lead["name"], "BLOCKED", verdict.reason))
            continue

        copy = personalize(lead, market)["copy"][lang]
        if channel == "email":
            if live:
                _send_email(lead["email"], copy["email_subject"], copy["email_body"])
        elif channel == "whatsapp":
            if live:
                _send_whatsapp(lead["phone"], lead["name"], lead["demo_link"])
        elif channel == "call_list":
            call_rows.append({"name": lead["name"], "phone": lead["phone"], "district": lead["district"],
                              "score": lead["score"], "why": lead["score_reasons"],
                              "demo_link": lead["demo_link"], "script": copy["call_script"]})
        else:
            raise ValueError(f"unknown channel {channel}")

        # A call list is a hand-off: the human records 'contacted' after dialling.
        if live and channel != "call_list":
            memory.record(market.id, "contacted", lead_id=lead["id"], channel=channel)
        results["sent"] += 1
        results["items"].append((lead["name"], "SENT" if live else "WOULD SEND", channel))

    if call_rows:
        out = DATA_DIR / f"call_list_{market.id}.csv"
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(call_rows[0]))
            w.writeheader()
            w.writerows(call_rows)
        results["file"] = str(out)
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
