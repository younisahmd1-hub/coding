"""Command line for the Vocaris organism.

    python -m organism.cli status                      # whole-organism view: every market, funnel, diagnosis
    python -m organism.cli source  --market dubai      # find businesses (Google Places)
    python -m organism.cli import-csv leads.csv --market dubai
    python -m organism.cli enrich  --market dubai      # find generic business emails on websites
    python -m organism.cli score   --market dubai
    python -m organism.cli personalize --market dubai
    python -m organism.cli set-demo <lead_id> <slug>  # use the slug the Vocaris backend created
    python -m organism.cli verify-links --market dubai # only live demo pages may be sent
    python -m organism.cli top     --market dubai -n 20
    python -m organism.cli mark-tested <lead_id>       # after YOU called the demo and it held up
    python -m organism.cli outreach --market dubai --channel linkedin   # drafts to outbox/, never sends
    python -m organism.cli record <lead_id> <event> [--channel email] [--cost 0]
    python -m organism.cli optout <phone_or_email>
    python -m organism.cli allocate --capacity 100
    python -m organism.cli ads-plan --market dubai
    python -m organism.cli kill on|off
"""
from __future__ import annotations

import argparse
import sys

from . import brain, immune
from .markets import load_markets
from .memory import Memory
from .organs import outreach, personalize, scoring, sourcing


def _market(markets, mid):
    if mid not in markets:
        sys.exit(f"unknown market '{mid}'. known: {', '.join(markets)}")
    return markets[mid]


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="organism")
    p.add_argument("--db", help="path to SQLite memory (default data/organism.db)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status")
    for name in ("source", "score", "personalize", "enrich", "ads-plan"):
        s = sub.add_parser(name)
        s.add_argument("--market", required=True)
        if name == "source":
            s.add_argument("--segments", nargs="*")
            s.add_argument("--districts", nargs="*")
            s.add_argument("--pages", type=int, default=3)
        if name == "personalize":
            s.add_argument("--min-score", type=float, default=0)
        if name == "enrich":
            s.add_argument("--limit", type=int, default=100)
    s = sub.add_parser("verify-links")
    s.add_argument("--market", required=True)
    s = sub.add_parser("set-demo", help="map a lead to the slug the Vocaris backend created")
    s.add_argument("lead_id")
    s.add_argument("slug")
    s = sub.add_parser("import-csv")
    s.add_argument("path")
    s.add_argument("--market", required=True)
    s = sub.add_parser("top")
    s.add_argument("--market", required=True)
    s.add_argument("-n", type=int, default=20)
    s = sub.add_parser("outreach")
    s.add_argument("--market", required=True)
    s.add_argument("--channel", required=True, choices=outreach.CHANNELS)
    s.add_argument("--limit", type=int, default=5)
    s.add_argument("--min-score", type=float, default=0)
    s = sub.add_parser("mark-tested", help="you called the demo yourself and it held up")
    s.add_argument("lead_id")
    s = sub.add_parser("record")
    s.add_argument("lead_id")
    s.add_argument("event", choices=["contacted", "replied", "demo_called", "trial", "paid", "lost",
                                     "whatsapp_opt_in"])
    s.add_argument("--channel")
    s.add_argument("--cost", type=float, default=0)
    s = sub.add_parser("spend")
    s.add_argument("--market", required=True)
    s.add_argument("--channel", default="ads")
    s.add_argument("usd", type=float)
    s = sub.add_parser("optout")
    s.add_argument("contact")
    s = sub.add_parser("allocate")
    s.add_argument("--capacity", type=int, default=100)
    s = sub.add_parser("kill")
    s.add_argument("state", choices=["on", "off"])
    s.add_argument("--reason", default="")

    a = p.parse_args(argv)
    markets = load_markets()
    mem = Memory(a.db)

    if a.cmd == "status":
        print(f"KILL SWITCH: {'ON' if immune.kill_switch_on() else 'off'}\n")
        for m in markets.values():
            f = brain.funnel(m, mem)
            print(f"■ {m.name} [{m.status}]  leads={f['leads']}  " +
                  "  ".join(f"{k}={f[k]}" for k in brain.FUNNEL) +
                  f"  spend=${f['spend_usd']}" +
                  (f"  target {f['paid']}/{f['target_paid']} ({f['progress_pct']}%)" if f["target_paid"] else ""))
            if m.active:
                for note in brain.diagnose(m, mem):
                    print(f"    • {note}")
        return

    if a.cmd == "kill":
        immune.set_kill_switch(a.state == "on", a.reason)
        print(f"kill switch {a.state}")
    elif a.cmd == "source":
        print(sourcing.source_market(_market(markets, a.market), mem, segments=a.segments,
                                     districts=a.districts, max_pages=a.pages))
    elif a.cmd == "import-csv":
        print(sourcing.import_csv(a.path, _market(markets, a.market), mem))
    elif a.cmd == "enrich":
        found = 0
        rows = [r for r in mem.leads(market=a.market, order_by_score=True) if r["website"] and not r["email"]]
        for r in rows[: a.limit]:
            email = sourcing.find_business_email(r["website"])
            if email:
                mem.update_lead(r["id"], email=email)
                found += 1
        print(f"checked {min(len(rows), a.limit)} websites, found {found} business emails")
    elif a.cmd == "verify-links":
        print(personalize.verify_market(_market(markets, a.market), mem))
    elif a.cmd == "set-demo":
        lead = mem.lead(a.lead_id) or sys.exit(f"no lead {a.lead_id}")
        m = markets[lead["market"]]
        mem.update_lead(a.lead_id, slug=a.slug, demo_link=m.demo_link_template.format(slug=a.slug),
                        demo_verified=int(personalize.demo_page_live(a.slug)))
        print("live" if mem.lead(a.lead_id)["demo_verified"] else "saved, but demo page is NOT live yet")
    elif a.cmd == "score":
        print(f"scored {scoring.score_market(_market(markets, a.market), mem)} leads")
    elif a.cmd == "personalize":
        print(f"created {personalize.personalize_market(_market(markets, a.market), mem, a.min_score)} demo links")
    elif a.cmd == "top":
        for r in mem.leads(market=a.market, order_by_score=True, limit=a.n):
            print(f"{r['score'] or 0:6.1f}  {r['name'][:38]:38}  {r['segment'] or '':12} {r['district'] or '':15} "
                  f"{r['phone'] or '-':16} {r['stage']}")
    elif a.cmd == "outreach":
        res = outreach.run(_market(markets, a.market), a.channel, mem, a.limit, a.min_score)
        for name, status, why in res["items"]:
            print(f"  {status:10} {name[:40]:40} {why}")
        print(f"{res['drafted']} drafts in outbox/ (nothing sent), {res['blocked']} blocked")
        for f in res["files"]:
            print(f"    {f}")
    elif a.cmd == "mark-tested":
        if not mem.lead(a.lead_id):
            sys.exit(f"no lead {a.lead_id}")
        mem.update_lead(a.lead_id, call_tested=1)
        print("marked as call-tested")
    elif a.cmd == "record":
        lead = mem.lead(a.lead_id)
        if not lead:
            sys.exit(f"no lead {a.lead_id}")
        if a.event == "whatsapp_opt_in":
            mem.update_lead(a.lead_id, whatsapp_opt_in=1)
        else:
            mem.record(lead["market"], a.event, lead_id=a.lead_id, channel=a.channel, cost_usd=a.cost)
        print("recorded")
    elif a.cmd == "spend":
        mem.record(a.market, "ad_spend", channel=a.channel, cost_usd=a.usd)
        print("recorded")
    elif a.cmd == "optout":
        mem.suppress(a.contact)
        print("suppressed")
    elif a.cmd == "allocate":
        for arm in brain.allocate(markets, mem, a.capacity):
            print(f"{arm['market']:10} {arm['channel']:10} p_best={arm['p_best']:.2f}  "
                  f"conv={arm['conv_rate']}  ({arm['trials']}/{arm['contacted']})  -> {arm['allocated']} contacts")
    elif a.cmd == "ads-plan":
        for row in outreach.ads_plan(_market(markets, a.market), mem):
            print(row)


if __name__ == "__main__":
    main()
