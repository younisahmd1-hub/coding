# Repository guide

- Start at `Medirian_Holdings/CURRENT_STATE.md`, then `Medirian_Holdings/MASTER_ROUTE.md`.
- Group brain (Meridian Holdings + Vocaris, since 2026-10-10): the claude.ai project «The main manager» holds the
  canonical `claude/brain/CURRENT_STATE_AR.md`, `BRAIN_MAP_AR.md` (one RT-01…RT-24 index for both houses) and
  `PIPELINES_AR.md`; a dated mirror lives in the Meridian laptop folder `00_BRAIN`. This repo covers Vocaris only.
- Vocaris work: read `Medirian_Holdings/10_COMPANIES/vocaris/CLAUDE.md` (house rules) and
  `VOCARIS_MASTER_KNOWLEDGE.md` in the same folder before anything else. Replies to Ahmad are in Arabic.
- Tests: `cd Medirian_Holdings/10_COMPANIES/vocaris && python3 -m unittest discover -s tests -t .`
- Never commit secrets; runtime data (`data/`, `outbox/`) is gitignored.
