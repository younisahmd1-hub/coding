# RT-01: FILE_ROUTE

| ID | Path | Purpose |
|---|---|---|
| F-001 | CURRENT_STATE.md | Live operating state — read first every session |
| F-002 | MASTER_ROUTE.md | Index of all routes |
| F-003 | 10_COMPANIES/vocaris/README.md | Vocaris organism manual |
| F-004 | 10_COMPANIES/vocaris/markets/*.yaml | Market cells (one per city) |
| F-006 | 10_COMPANIES/vocaris/CLAUDE.md | Vocaris house rules (auto-read by Claude Code in that folder) |
| F-007 | 10_COMPANIES/vocaris/VOCARIS_MASTER_KNOWLEDGE.md | Single source of Vocaris knowledge |
| F-008 | 10_COMPANIES/vocaris/PROGRESS_LOG.md | Session log — newest first, entry required each session |
| F-009 | 10_COMPANIES/vocaris/SYNC_STATE.md | Last sync with claude.ai chats |
| F-010 | 10_COMPANIES/vocaris/outbox/ | Drafts for Ahmad to send by hand (gitignored) |
| F-005 | 10_COMPANIES/vocaris/data/ | Runtime data (gitignored: SQLite memory, call lists, kill switch) |
| F-011 | 20_PLUGINS/omniroute/ | Claude Code plugin for the OmniRoute gateway (manifest, .mcp.json, skills, README) |
| F-012 | ../.claude-plugin/marketplace.json | Plugin marketplace `medirian` (repo root) |
| F-013 | 30_GOVERNANCE/COUNCIL.md | R26 island councils: seats, vote rule, red lines, owner seal/veto |
| F-014 | 30_GOVERNANCE/COUNCIL_CLERK_PROMPT.md | Exact prompt of the on-demand council clerk routine |
| F-015 | 30_GOVERNANCE/village_council.js | Reference copy of the council code published in the village page |
