"""Memory: a single SQLite file holding leads, funnel events and the suppression (opt-out) list."""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from . import DATA_DIR

SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    id TEXT PRIMARY KEY,            -- source:place_id
    market TEXT NOT NULL,
    segment TEXT,
    district TEXT,
    name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    website TEXT,
    address TEXT,
    rating REAL,
    review_count INTEGER,
    maps_url TEXT,
    raw TEXT,                       -- full source payload (JSON)
    score REAL,
    score_reasons TEXT,
    slug TEXT,
    demo_link TEXT,
    demo_verified INTEGER DEFAULT 0,    -- 1 once the demo page returned 200
    whatsapp_opt_in INTEGER DEFAULT 0,
    stage TEXT DEFAULT 'found',     -- found > scored > contacted > replied > demo_called > trial > paid | lost
    created_at REAL,
    updated_at REAL
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id TEXT,
    market TEXT NOT NULL,
    channel TEXT,
    type TEXT NOT NULL,             -- contacted | replied | demo_called | trial | paid | lost | ad_spend
    cost_usd REAL DEFAULT 0,
    meta TEXT,
    ts REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS suppression (
    contact TEXT PRIMARY KEY,       -- normalized phone or lowercased email
    reason TEXT,
    ts REAL
);
CREATE INDEX IF NOT EXISTS idx_leads_market_stage ON leads(market, stage);
CREATE INDEX IF NOT EXISTS idx_events_market_type ON events(market, type, ts);
"""

STAGES = ["found", "scored", "contacted", "replied", "demo_called", "trial", "paid"]


class Memory:
    def __init__(self, path: Path | str | None = None):
        path = Path(path) if path else DATA_DIR / "organism.db"
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    # ---- leads -------------------------------------------------------------
    def upsert_lead(self, lead: dict) -> bool:
        """Insert a lead; on conflict refresh source fields but keep stage/score. Returns True if new."""
        now = time.time()
        exists = self.db.execute("SELECT 1 FROM leads WHERE id=?", (lead["id"],)).fetchone()
        cols = ["market", "segment", "district", "name", "phone", "email", "website",
                "address", "rating", "review_count", "maps_url"]
        values = [lead.get(c) for c in cols]
        raw = json.dumps(lead.get("raw") or {}, ensure_ascii=False)
        if exists:
            sets = ", ".join(f"{c}=COALESCE(?, {c})" for c in cols)
            self.db.execute(f"UPDATE leads SET {sets}, raw=?, updated_at=? WHERE id=?",
                            [*values, raw, now, lead["id"]])
        else:
            self.db.execute(
                f"INSERT INTO leads (id, {', '.join(cols)}, raw, created_at, updated_at) "
                f"VALUES (?, {', '.join('?' * len(cols))}, ?, ?, ?)",
                [lead["id"], *values, raw, now, now])
        self.db.commit()
        return not exists

    def leads(self, market: str | None = None, stage: str | None = None,
              order_by_score: bool = False, limit: int | None = None) -> list[sqlite3.Row]:
        sql, args = "SELECT * FROM leads WHERE 1=1", []
        if market:
            sql += " AND market=?"
            args.append(market)
        if stage:
            sql += " AND stage=?"
            args.append(stage)
        sql += " ORDER BY score DESC" if order_by_score else " ORDER BY created_at"
        if limit:
            sql += f" LIMIT {int(limit)}"
        return self.db.execute(sql, args).fetchall()

    def lead(self, lead_id: str) -> sqlite3.Row | None:
        return self.db.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()

    def update_lead(self, lead_id: str, **fields) -> None:
        fields["updated_at"] = time.time()
        sets = ", ".join(f"{k}=?" for k in fields)
        self.db.execute(f"UPDATE leads SET {sets} WHERE id=?", [*fields.values(), lead_id])
        self.db.commit()

    # ---- events ------------------------------------------------------------
    def record(self, market: str, type_: str, lead_id: str | None = None, channel: str | None = None,
               cost_usd: float = 0.0, meta: dict | None = None, ts: float | None = None) -> None:
        self.db.execute(
            "INSERT INTO events (lead_id, market, channel, type, cost_usd, meta, ts) VALUES (?,?,?,?,?,?,?)",
            (lead_id, market, channel, type_, cost_usd, json.dumps(meta or {}), ts or time.time()))
        if lead_id and type_ in STAGES + ["lost"]:
            row = self.lead(lead_id)
            # stages only move forward; 'lost' is terminal unless the lead later re-engages
            current = STAGES.index(row["stage"]) if row and row["stage"] in STAGES else -1
            if row and (type_ == "lost" or STAGES.index(type_) > current):
                self.db.execute("UPDATE leads SET stage=?, updated_at=? WHERE id=?",
                                (type_, time.time(), lead_id))
        self.db.commit()

    def count_events(self, market: str, type_: str, channel: str | None = None,
                     since: float | None = None) -> int:
        sql, args = "SELECT COUNT(*) FROM events WHERE market=? AND type=?", [market, type_]
        if channel:
            sql += " AND channel=?"
            args.append(channel)
        if since:
            sql += " AND ts>=?"
            args.append(since)
        return self.db.execute(sql, args).fetchone()[0]

    def spend(self, market: str, channel: str | None = None) -> float:
        sql, args = "SELECT COALESCE(SUM(cost_usd),0) FROM events WHERE market=?", [market]
        if channel:
            sql += " AND channel=?"
            args.append(channel)
        return self.db.execute(sql, args).fetchone()[0]

    # ---- suppression -------------------------------------------------------
    def suppress(self, contact: str, reason: str = "opt_out") -> None:
        self.db.execute("INSERT OR REPLACE INTO suppression VALUES (?,?,?)",
                        (normalize_contact(contact), reason, time.time()))
        self.db.commit()

    def is_suppressed(self, contact: str | None) -> bool:
        if not contact:
            return False
        return self.db.execute("SELECT 1 FROM suppression WHERE contact=?",
                               (normalize_contact(contact),)).fetchone() is not None


def normalize_contact(contact: str) -> str:
    contact = contact.strip()
    if "@" in contact:
        return contact.lower()
    return "".join(ch for ch in contact if ch.isdigit() or ch == "+")
