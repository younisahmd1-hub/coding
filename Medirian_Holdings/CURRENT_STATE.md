# CURRENT STATE — Medirian Holdings

_Last updated: 2026-10-08_

## Active focus
**Vocaris worldwide growth organism**, at `10_COMPANIES/vocaris/`. Version 0.1 is built and its 11 tests pass. It has not been given real leads yet.

## Status by market
| Market | Status | Leads | Paid | Target |
|---|---|---|---|---|
| Dubai | active | 0 | 0 | 100 paying by month 3 |
| Riyadh | planned (months 7–9) | 0 | 0 | — |

## Blockers, most urgent first
1. **SECURITY (critical):** the live vocaris.ai JavaScript exposes the production database password. The technical partner must rotate the Neon password and move secrets to the server. See RT-13.
2. **No leads yet.** Run `source` once a `GOOGLE_PLACES_API_KEY` is set, or import a CSV.
3. **Demo links:** personal demo pages (`vocaris.ai/demo/<slug>`) are created by the Vocaris backend pipeline. The organism only sends links that have been checked and confirmed live.
4. **Product gaps for the UAE:** no Arabic agent language, no WhatsApp, no Fresha, prices in USD only.
5. **Telephony path not decided:** A = IFZA free-zone company with local numbers (about $3.5–4.7k); B = WhatsApp-only through the US company.
6. Outreach credentials (SMTP, WhatsApp Cloud API) are not configured, so every send is a dry run.

## Next actions
- [ ] Partner: rotate the database credential.
- [ ] Get a Google Places API key, then source and score Dubai (Jumeirah and Dubai Marina first).
- [ ] Decide between telephony path A and B.
- [ ] Partner: add Arabic to the agent languages and build a Fresha integration.
- [ ] Set up a sending domain and SMTP, then start an email warm-up of 40 per day.
- [ ] Run paid ads with the "message us on WhatsApp" call to action, which gives inbound WhatsApp opt-ins.

## Sources consulted
- Google Drive folder `vocaris`: the UAE markets report, CPaaS/TDRA notes, fast-launch options, ad scripts, the C1 film treatment.
- The live vocaris.ai site and its public API.
- Desktop: not reached. The laptop is offline.
