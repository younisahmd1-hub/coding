# CURRENT STATE — Medirian Holdings

_Last updated: 2026-10-10_

## Group brain
The group-wide state (Meridian Holdings + Vocaris) lives in the claude.ai project «The main manager» under `claude/brain/`, with a dated mirror in the Meridian laptop folder `00_BRAIN`. This file covers the Vocaris work in this repository only.

## Read first for Vocaris
`10_COMPANIES/vocaris/CLAUDE.md` (house rules, in Arabic) → `VOCARIS_MASTER_KNOWLEDGE.md` → `PROGRESS_LOG.md`.
All outputs to Ahmad are in Arabic and end with: what was done · decision needed · next step.

## Active focus
**Vocaris worldwide growth organism**, at `10_COMPANIES/vocaris/`. Version 0.2 follows the house rules in CLAUDE.md (drafts only, 5 a day, call-tested demos); 14 tests pass. It has not been given real leads yet.

## Tooling
**Claude Code plugin `omniroute`** at `20_PLUGINS/omniroute/` (install: `/plugin marketplace add younisahmd1-hub/coding`, then `/plugin install omniroute@medirian`). Needs `OMNIROUTE_API_KEY`; MCP tools also need the gateway's MCP transport set to streamable-http.

## Status by market
| Market | Status | Leads | Paid | Target |
|---|---|---|---|---|
| Dubai | active (first market NOT yet confirmed by Ahmad) | 0 | 0 | 1 real customer who forwarded their phone |
| Riyadh | planned (months 7–9) | 0 | 0 | — |

## Blockers, most urgent first
1. **Security:** one open item is tracked privately with Ahmad and the technical partner. Details stay out of this repository on purpose. See RT-13.
2. **No leads in this repository.** Lead data is kept outside the repo on purpose (privacy and compliance first). The engine runs `source` once a `GOOGLE_PLACES_API_KEY` is set, or imports a CSV.
3. **Demo links:** personal demo pages (`vocaris.ai/demo/<slug>`) are created by the Vocaris backend pipeline. Drafts only include links that are live AND that Ahmad has called himself.
4. **Product gaps for the UAE:** no Arabic agent language, no WhatsApp, no Fresha, prices in USD only.
5. **Telephony path not decided:** A = IFZA free-zone company with local numbers (about $3.5–4.7k); B = WhatsApp-only through the US company.
6. Outreach is drafts-only by design: Ahmad sends every message by hand.

## Next actions
- [ ] Partner: close the private security item (RT-13).
- [ ] Get a Google Places API key, then source and score Dubai (Jumeirah and Dubai Marina first).
- [ ] Decide between telephony path A and B.
- [ ] Partner: add Arabic to the agent languages and build a Fresha integration.
- [ ] Set up a sending domain and SMTP, then start an email warm-up of 40 per day.
- [ ] Run paid ads with the "message us on WhatsApp" call to action, which gives inbound WhatsApp opt-ins.

## Sources consulted
- Google Drive folder `vocaris`: the UAE markets report, CPaaS/TDRA notes, fast-launch options, ad scripts, the C1 film treatment.
- The live vocaris.ai site and its public API.
- Laptop: reached on 2026-10-10. The Vocaris HQ there (Claude Code) now has 40 agents in 10 rooms; its `bus/ROSTER.md` is the reference.
