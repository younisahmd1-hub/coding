"""Scoring organ: ranks leads by how much a missed-call problem costs them and how easy they are to win.

Transparent points, not a black box — every score comes with its reasons so a human can sanity-check it.
"""
from __future__ import annotations

import json

from ..markets import Market


def score_lead(lead: dict, market: Market) -> tuple[float, list[str]]:
    cfg = market.scoring
    score, reasons = 0.0, []

    if not lead.get("phone"):
        return 0.0, ["no phone number — cannot be a Vocaris customer"]

    reviews = lead.get("review_count") or 0
    rating = lead.get("rating")
    busy = cfg.get("busy_review_count", 150)

    # Volume: more reviews => more customers => more calls to miss.
    volume = min(reviews / busy, 2.0) * 30
    score += volume
    reasons.append(f"volume +{volume:.0f} ({reviews} reviews)")

    # Quality: well-rated businesses care about service and can afford it.
    if rating is not None:
        if rating >= cfg.get("min_rating", 4.0):
            score += 20
            reasons.append(f"rating {rating} +20")
        else:
            score -= 10
            reasons.append(f"rating {rating} -10")

    if lead.get("website"):
        score += 10 if cfg.get("prefer_website") else 5
        reasons.append("has website")

    raw = lead.get("raw") or {}
    if isinstance(raw, str):
        raw = json.loads(raw or "{}")
    blob = json.dumps(raw).lower() + (lead.get("website") or "").lower()
    for platform in cfg.get("booking_platforms_bonus", []):
        if platform in blob:
            score += 10
            reasons.append(f"uses {platform} (direct integration) +10")
            break

    # Long opening hours => more out-of-hours calls a human can't take.
    hours = (raw.get("regularOpeningHours") or {}).get("periods") or []
    if hours:
        late = sum(1 for p in hours if (p.get("close") or {}).get("hour", 0) >= 21
                   or (p.get("close") or {}).get("hour", 99) < 4)
        if late >= 3:
            score += 10
            reasons.append(f"open late {late} days/week +10")

    weight = (market.segments.get(lead.get("segment") or "", {}) or {}).get("weight", 1.0)
    if weight != 1.0:
        reasons.append(f"segment weight x{weight}")
    return round(score * weight, 1), reasons


def score_market(market: Market, memory) -> int:
    n = 0
    for row in memory.leads(market=market.id):
        lead = dict(row)
        score, reasons = score_lead(lead, market)
        stage = "scored" if lead["stage"] == "found" else lead["stage"]
        memory.update_lead(lead["id"], score=score, score_reasons="; ".join(reasons), stage=stage)
        n += 1
    return n
