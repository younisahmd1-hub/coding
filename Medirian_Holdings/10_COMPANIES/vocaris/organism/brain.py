"""Brain: watches every market cell's funnel and decides where the next unit of effort goes.

Method: each (market, channel) pair is an arm of a multi-armed bandit. Its chance of turning a contact into a
trial gets a Beta posterior from real counts; Thompson sampling then splits capacity toward arms that are
winning while still exploring the rest. No numbers are assumed — with no data every arm is treated equally.
"""
from __future__ import annotations

import random

from .markets import Market

FUNNEL = ["contacted", "replied", "demo_called", "trial", "paid"]
OUTREACH_CHANNELS = ["linkedin", "email", "whatsapp", "call_list"]


def funnel(market: Market, memory) -> dict:
    counts = {"leads": len(memory.leads(market=market.id))}
    for stage in FUNNEL:
        counts[stage] = memory.count_events(market.id, stage)
    counts["spend_usd"] = round(memory.spend(market.id), 2)
    counts["cost_per_trial"] = round(counts["spend_usd"] / counts["trial"], 2) if counts["trial"] else None
    counts["cost_per_paid"] = round(counts["spend_usd"] / counts["paid"], 2) if counts["paid"] else None
    target = market.targets.get("paying_customers_by_month_3")
    counts["target_paid"] = target
    counts["progress_pct"] = round(100 * counts["paid"] / target, 1) if target else None
    return counts


def arm_stats(market: Market, channel: str, memory) -> tuple[int, int]:
    contacted = memory.count_events(market.id, "contacted", channel=channel)
    trials = memory.db.execute(
        "SELECT COUNT(DISTINCT e.lead_id) FROM events e WHERE e.market=? AND e.type='trial' AND e.lead_id IN "
        "(SELECT lead_id FROM events WHERE market=? AND channel=? AND type='contacted')",
        (market.id, market.id, channel)).fetchone()[0]
    return contacted, trials


def allocate(markets: dict[str, Market], memory, capacity: int = 100, draws: int = 2000,
             rng: random.Random | None = None) -> list[dict]:
    """Split `capacity` contacts across active (market, channel) arms by probability of being best."""
    rng = rng or random.Random(7)
    arms = []
    for m in markets.values():
        if not m.active:
            continue
        for ch in OUTREACH_CHANNELS:
            if m.channel(ch).get("enabled"):
                n, k = arm_stats(m, ch, memory)
                arms.append({"market": m.id, "channel": ch, "contacted": n, "trials": k,
                             "cap": m.channel(ch).get("daily_cap", 0)})
    if not arms:
        return []

    wins = [0] * len(arms)
    for _ in range(draws):
        samples = [rng.betavariate(1 + a["trials"], 1 + a["contacted"] - a["trials"]) for a in arms]
        wins[max(range(len(arms)), key=samples.__getitem__)] += 1

    explore_floor = 0.1 / len(arms)
    for a, w in zip(arms, wins):
        a["p_best"] = round(w / draws, 3)
        a["conv_rate"] = round(a["trials"] / a["contacted"], 3) if a["contacted"] else None
        share = explore_floor + 0.9 * w / draws
        a["allocated"] = min(a["cap"], round(capacity * share))
    return sorted(arms, key=lambda a: -a["p_best"])


def diagnose(market: Market, memory) -> list[str]:
    """Plain-language findings: where the funnel leaks and what to do next."""
    f = funnel(market, memory)
    notes = []
    if f["leads"] == 0:
        return [f"{market.name}: no leads yet — run `source` (needs GOOGLE_PLACES_API_KEY) or `import-csv`."]
    unscored = len(memory.leads(market=market.id, stage="found"))
    if unscored:
        notes.append(f"{unscored} leads unscored — run `score`.")
    no_link = memory.db.execute("SELECT COUNT(*) FROM leads WHERE market=? AND stage='scored' AND demo_link IS NULL",
                                (market.id,)).fetchone()[0]
    if no_link:
        notes.append(f"{no_link} scored leads have no demo link — run `personalize`.")
    if f["contacted"] == 0:
        notes.append("Nobody contacted yet — the organism has no feedback to learn from.")
    for a, b in zip(FUNNEL, FUNNEL[1:]):
        if f[a] >= 30 and f[b] / f[a] < 0.05:
            notes.append(f"Leak: only {f[b]}/{f[a]} go from {a} to {b} — test new copy/offer at this step.")
    if market.telephony.get("path") == "undecided":
        notes.append("Telephony path undecided (A: IFZA local numbers vs B: WhatsApp-only) — blocks scale.")
    unverified = memory.db.execute("SELECT COUNT(*) FROM leads WHERE market=? AND slug IS NOT NULL "
                                   "AND demo_verified=0", (market.id,)).fetchone()[0]
    if unverified and market.require_verified_demo:
        notes.append(f"{unverified} demo links not live yet — create them in the Vocaris outreach pipeline "
                     "(`set-demo` to map the real slug), then `verify-links`.")
    untested = memory.db.execute("SELECT COUNT(*) FROM leads WHERE market=? AND demo_verified=1 "
                                 "AND call_tested=0", (market.id,)).fetchone()[0]
    if untested:
        notes.append(f"{untested} live demos not call-tested — call each one yourself, then `mark-tested`.")
    for gap in market.product_gaps:
        notes.append(f"Product gap: {gap}")
    return notes or ["Healthy — keep feeding the winning arms."]

