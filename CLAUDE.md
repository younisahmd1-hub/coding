# Repository guide

- Start at `Medirian_Holdings/CURRENT_STATE.md`, then `Medirian_Holdings/MASTER_ROUTE.md`.
- Vocaris work: read `Medirian_Holdings/10_COMPANIES/vocaris/CLAUDE.md` (house rules) and
  `VOCARIS_MASTER_KNOWLEDGE.md` in the same folder before anything else. Replies to Ahmad are in Arabic.
- Tests: `cd Medirian_Holdings/10_COMPANIES/vocaris && python3 -m unittest discover -s tests -t .`
- Never commit secrets; runtime data (`data/`, `outbox/`) is gitignored.
