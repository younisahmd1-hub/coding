# RT-13: SECURITY_ROUTE

- 2026-10-08: CRITICAL — vocaris.ai frontend bundle exposes the production Neon Postgres connection string (REACT_APP_DATABASE_URL). Owner must rotate the password and move secrets server-side. Value intentionally NOT recorded here.
- Secrets only via env vars; `data/` is gitignored.
