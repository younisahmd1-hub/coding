# RT-02: CODE_ROUTE

| ID | Path | Role |
|---|---|---|
| C-001 | 10_COMPANIES/vocaris/organism/cli.py | Command line entry point |
| C-002 | 10_COMPANIES/vocaris/organism/brain.py | Funnel metrics, Thompson-sampling allocation, diagnosis |
| C-003 | 10_COMPANIES/vocaris/organism/immune.py | Compliance gate, caps, opt-outs, kill switch |
| C-004 | 10_COMPANIES/vocaris/organism/memory.py | SQLite: leads, events, suppression |
| C-005 | 10_COMPANIES/vocaris/organism/markets.py | Market cell loader |
| C-006 | 10_COMPANIES/vocaris/organism/organs/sourcing.py | Google Places + CSV import + business-email finder |
| C-007 | 10_COMPANIES/vocaris/organism/organs/scoring.py | Lead scoring with reasons |
| C-008 | 10_COMPANIES/vocaris/organism/organs/personalize.py | Demo links, bilingual copy, link verification |
| C-009 | 10_COMPANIES/vocaris/organism/organs/outreach.py | Email / WhatsApp / call list / ads plan |
| C-010 | 20_PLUGINS/omniroute/scripts/omni.py | OmniRoute /v1 CLI (ping, models, ask), used by the plugin skills |
| C-011 | 20_PLUGINS/omniroute/bin/omni | sh wrapper that finds Python 3 (python3/python/py) and runs omni.py |
