"""Immune system: every outbound action must pass here first.

Protects the business from the things that kill outreach engines: banned WhatsApp numbers, burned email
domains, legal complaints, and runaway automation.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from . import DATA_DIR
from .markets import Market

KILL_SWITCH = DATA_DIR / "KILL_SWITCH"


@dataclass
class Verdict:
    allowed: bool
    reason: str

    def __bool__(self) -> bool:
        return self.allowed


def kill_switch_on() -> bool:
    return KILL_SWITCH.exists()


def set_kill_switch(on: bool, reason: str = "") -> None:
    if on:
        KILL_SWITCH.parent.mkdir(parents=True, exist_ok=True)
        KILL_SWITCH.write_text(f"{time.ctime()} {reason}\n")
    elif KILL_SWITCH.exists():
        KILL_SWITCH.unlink()


def check(lead: dict, market: Market, channel: str, memory, now: float | None = None) -> Verdict:
    now = now or time.time()
    if kill_switch_on():
        return Verdict(False, "kill switch is ON")
    if not market.active:
        return Verdict(False, f"market {market.id} is {market.status}")

    cfg = market.channel(channel)
    if not cfg.get("enabled"):
        return Verdict(False, f"channel {channel} disabled in {market.id}")

    contact = lead.get("email") if channel == "email" else lead.get("phone")
    if not contact:
        return Verdict(False, f"no {'email' if channel == 'email' else 'phone'} for lead")
    if memory.is_suppressed(contact):
        return Verdict(False, "contact opted out / suppressed")

    if market.require_verified_demo and not lead.get("demo_verified"):
        return Verdict(False, "demo page not verified live — run `verify-links` (never send a 404 link)")

    if lead.get("stage") in ("paid", "trial", "lost"):
        return Verdict(False, f"lead is already {lead['stage']}")

    if channel == "whatsapp" and not cfg.get("cold_allowed") and not lead.get("whatsapp_opt_in"):
        return Verdict(False, "WhatsApp needs prior opt-in (Meta Business policy)")
    if channel in ("email", "call_list") and not cfg.get("cold_allowed") and lead.get("stage") in ("found", "scored"):
        return Verdict(False, f"cold {channel} not allowed in {market.id}")

    # one touch per lead per channel per 7 days
    recent = memory.db.execute(
        "SELECT 1 FROM events WHERE lead_id=? AND channel=? AND type='contacted' AND ts>=?",
        (lead["id"], channel, now - 7 * 86400)).fetchone()
    if recent:
        return Verdict(False, "already contacted on this channel in the last 7 days")

    day_start = now - 86400
    sent_today = memory.count_events(market.id, "contacted", channel=channel, since=day_start)
    if sent_today >= cfg.get("daily_cap", 0):
        return Verdict(False, f"daily cap {cfg.get('daily_cap')} reached for {channel}")

    if channel == "call_list" and cfg.get("call_hours"):
        start, end = cfg["call_hours"]
        local_hour = datetime.fromtimestamp(now, ZoneInfo(market.timezone)).hour
        if not start <= local_hour < end:
            return Verdict(False, f"outside call hours {start}-{end} {market.timezone}")

    return Verdict(True, "ok")
