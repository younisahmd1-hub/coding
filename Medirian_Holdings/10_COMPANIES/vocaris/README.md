# Vocaris Growth Organism

A system that finds businesses that miss phone calls, gives each one its own Vocaris demo, contacts them through the channels each country allows, and learns where to put effort across every market.

## Anatomy

```
                 ┌──────────────── BRAIN (brain.py) ────────────────┐
                 │ funnel per market · Thompson-sampling allocation │
                 │ across (market × channel) · plain-English diagnosis │
                 └──────────────────────┬───────────────────────────┘
                                        │
   MARKET CELLS (markets/*.yaml)        ▼
   dubai ▸ riyadh ▸ …    ┌──── IMMUNE SYSTEM (immune.py) ────┐
   one YAML per city:    │ kill switch · market status ·     │
   districts, segments,  │ opt-outs · WhatsApp opt-in rule · │
   language, channels,   │ live demo link required · daily   │
   legal rules, gaps     │ caps · 7-day cooldown · call hours│
                         └──────────────┬────────────────────┘
                                        ▼
  ORGANS:  sourcing ─▶ scoring ─▶ personalize ─▶ outreach (email · WhatsApp · call list · ads plan)
                                        │
                                        ▼
                        MEMORY (memory.py, SQLite): leads · events · suppression
```

Every result (`replied`, `demo_called`, `trial`, `paid`) is recorded back into memory. The brain then shifts effort toward the market and channel combinations that turn contacts into trials.

## Quick start

```bash
cd Medirian_Holdings/10_COMPANIES/vocaris
export GOOGLE_PLACES_API_KEY=...                 # Google Cloud → Places API (New)

python3 -m organism.cli status                   # the whole organism at a glance
python3 -m organism.cli source --market dubai --segments barber salon --districts Jumeirah "Dubai Marina"
python3 -m organism.cli enrich --market dubai    # find info@/booking@ inboxes on business websites
python3 -m organism.cli score --market dubai
python3 -m organism.cli top --market dubai -n 30
python3 -m organism.cli personalize --market dubai
python3 -m organism.cli verify-links --market dubai   # only demo pages that exist may be sent
python3 -m organism.cli outreach --market dubai --channel call_list   # CSV + script for a human caller
python3 -m organism.cli outreach --market dubai --channel email       # dry run; add --live to send
python3 -m organism.cli record gplaces:XYZ trial
python3 -m organism.cli allocate --capacity 100
python3 -m organism.cli kill on --reason "pause everything"
```

Tests: `python3 -m unittest discover -s tests -t .`

## Growing into a new market
1. Copy `markets/_template.yaml` to `markets/<city>.yaml`.
2. Fill in districts, segments, languages and channel rules. Check that country's B2B outreach law before setting `cold_allowed: true`.
3. Set `status: active`. The brain includes it automatically.

## Channel rules built in
| Channel | Rule |
|---|---|
| WhatsApp | Only to leads who opted in, for example by messaging you from an ad. Meta bans numbers that start conversations with strangers. |
| Email | Only generic business inboxes (info@, booking@), always with a STOP option, under a daily warm-up cap. |
| Call list | Only inside business hours in the market's timezone. A human dials, then records the outcome. |
| Ads | Districts are weighted by the lead quality found in each. |

## Honest limits
- No result is promised. The brain decides only from real conversion counts, and with no data every option gets equal effort.
- Demo pages come from the Vocaris backend. This system checks that they exist before sending them.
- Message copy only claims features the live product has. See `product_gaps` in each market file.
