"""Market cells: one YAML file per city in markets/. Files starting with '_' are templates."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import MARKETS_DIR


@dataclass
class Market:
    id: str
    name: str
    country: str
    status: str
    currency: str
    languages: list[str]
    phone_country_code: str
    districts: list[str]
    segments: dict[str, dict]
    scoring: dict
    demo_link_template: str
    channels: dict[str, dict]
    offer: dict = field(default_factory=dict)
    telephony: dict = field(default_factory=dict)
    targets: dict = field(default_factory=dict)
    product_gaps: list[str] = field(default_factory=list)
    require_verified_demo: bool = True
    daily_total_cap: int = 5          # house rule: max 5 messages a day, all channels
    timezone: str = "Etc/UTC"
    dialect: str | None = None

    @property
    def active(self) -> bool:
        return self.status == "active"

    def channel(self, name: str) -> dict:
        return self.channels.get(name) or {"enabled": False}


def load_market(path: Path) -> Market:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    known = Market.__dataclass_fields__
    return Market(**{k: v for k, v in raw.items() if k in known})


def load_markets(directory: Path = MARKETS_DIR) -> dict[str, Market]:
    markets = {}
    for path in sorted(directory.glob("*.yaml")):
        if path.name.startswith("_"):
            continue
        market = load_market(path)
        markets[market.id] = market
    return markets
