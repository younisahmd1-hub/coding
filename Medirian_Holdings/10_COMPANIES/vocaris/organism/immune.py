"""Immune system: every outbound draft must pass here first.

Encodes the house rules in CLAUDE.md: protect Vocaris's reputation before any deal — no broken or untested demo
goes out, no spam, respect "don't contact me", max 5 messages a day, 5 touches over 14 days then 90-day archive.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from . import DATA_DIR
from .markets import Market

KILL_SWITCH = DATA_DIR / "KILL_SWITCH"
DAY = 86400
CADENCE_DAYS = [0, 3, 7, 11, 14]     # touch n is due this many days after the first touch
ARCHIVE_DAYS = 90
HUMAN_STAGES = ("replied", "demo_called", "trial", "paid", "lost")   # past these, Ahmad talks personally


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


def touches(lead_id: str, memory) -> list[float]:
    rows = memory.db.execute("SELECT ts FROM events WHERE lead_id=? AND type='contacted' ORDER BY ts",
                             (lead_id,)).fetchall()
    return [r[0] for r in rows]


def check(lead: dict, market: Market, channel: str, memory, now: float | None = None) -> Verdict:
    now = now or time.time()
    if kill_switch_on():
        return Verdict(False, "kill switch is ON")
    if not market.active:
        return Verdict(False, f"market {market.id} is {market.status}")

    cfg = market.channel(channel)
    if not cfg.get("enabled"):
        return Verdict(False, f"channel {channel} disabled in {market.id}")

    if channel == "email":
        contact = lead.get("email")
    elif channel == "linkedin":
        contact = lead.get("website") or lead.get("name")   # sent by hand from LinkedIn; suppression by name
    else:
        contact = lead.get("phone")
    if not contact:
        return Verdict(False, f"no contact detail for {channel}")
    if memory.is_suppressed(contact) or memory.is_suppressed(lead.get("phone") or "") \
            or memory.is_suppressed(lead.get("email") or ""):
        return Verdict(False, "asked not to be contacted")

    # Protect the brand: the personal demo must exist AND Ahmad must have called it himself.
    if market.require_verified_demo and not lead.get("demo_verified"):
        return Verdict(False, "demo page not live — create it, then `verify-links`")
    if not lead.get("call_tested"):
        return Verdict(False, "demo not call-tested yet — call it yourself, then `mark-tested`")

    if lead.get("stage") in HUMAN_STAGES:
        return Verdict(False, f"lead is {lead['stage']} — handle personally, not by sequence")

    if channel == "whatsapp" and not cfg.get("cold_allowed") and not lead.get("whatsapp_opt_in"):
        return Verdict(False, "WhatsApp needs prior opt-in (Meta Business policy)")
    if not cfg.get("cold_allowed") and lead.get("stage") in ("found", "scored") and channel != "whatsapp":
        return Verdict(False, f"cold {channel} not allowed in {market.id}")

    # Sequence: 5 touches over 14 days (days 0,3,7,11,14), then archive for 90 days.
    done = touches(lead["id"], memory)
    if len(done) >= len(CADENCE_DAYS):
        if now < done[-1] + ARCHIVE_DAYS * DAY:
            return Verdict(False, f"5 touches done — archived until {_date(done[-1] + ARCHIVE_DAYS * DAY)}")
    elif done:
        due = done[0] + CADENCE_DAYS[len(done)] * DAY
        if now < due:
            return Verdict(False, f"touch {len(done) + 1} not due until {_date(due)}")

    # Max messages per day across ALL channels (drafts reserve a slot).
    drafted_today = memory.db.execute(
        "SELECT COUNT(*) FROM events WHERE market=? AND type='drafted' AND ts>=?",
        (market.id, now - DAY)).fetchone()[0]
    if drafted_today >= market.daily_total_cap:
        return Verdict(False, f"daily limit {market.daily_total_cap} reached")
    if memory.db.execute("SELECT 1 FROM events WHERE lead_id=? AND type='drafted' AND ts>=?",
                         (lead["id"], now - DAY)).fetchone():
        return Verdict(False, "already drafted for this lead today")

    if channel == "call_list" and cfg.get("call_hours"):
        start, end = cfg["call_hours"]
        local_hour = datetime.fromtimestamp(now, ZoneInfo(market.timezone)).hour
        if not start <= local_hour < end:
            return Verdict(False, f"outside call hours {start}-{end} {market.timezone}")

    return Verdict(True, f"ok (touch {len(done) + 1}/5)")


def _date(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
