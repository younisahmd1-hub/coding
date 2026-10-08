"""Sourcing organ: finds businesses for a market cell.

Sources:
  * Google Places API (New) Text Search — needs GOOGLE_PLACES_API_KEY.
  * CSV import — for lists exported from anywhere else (columns: name, phone, email, website, ...).
"""
from __future__ import annotations

import csv
import os
import re
from pathlib import Path
from typing import Iterator

import requests

from ..markets import Market

PLACES_URL = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = ",".join([
    "places.id", "places.displayName", "places.formattedAddress", "places.internationalPhoneNumber",
    "places.nationalPhoneNumber", "places.websiteUri", "places.rating", "places.userRatingCount",
    "places.googleMapsUri", "places.types", "places.businessStatus", "places.regularOpeningHours",
    "nextPageToken",
])


class SourcingError(RuntimeError):
    pass


def places_search(query: str, api_key: str, max_pages: int = 3, session=requests) -> Iterator[dict]:
    """Yield raw place dicts for a text query. Places caps each query at 3 pages x 20 results."""
    body = {"textQuery": query, "pageSize": 20}
    headers = {"X-Goog-Api-Key": api_key, "X-Goog-FieldMask": FIELD_MASK}
    for _ in range(max_pages):
        resp = session.post(PLACES_URL, json=body, headers=headers, timeout=30)
        if resp.status_code != 200:
            raise SourcingError(f"Places API {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        yield from data.get("places", [])
        token = data.get("nextPageToken")
        if not token:
            return
        body = {"textQuery": query, "pageSize": 20, "pageToken": token}


def place_to_lead(place: dict, market: Market, segment: str, district: str) -> dict | None:
    if place.get("businessStatus") not in (None, "OPERATIONAL"):
        return None
    return {
        "id": f"gplaces:{place['id']}",
        "market": market.id,
        "segment": segment,
        "district": district,
        "name": (place.get("displayName") or {}).get("text", "").strip(),
        "phone": place.get("internationalPhoneNumber") or place.get("nationalPhoneNumber"),
        "website": place.get("websiteUri"),
        "address": place.get("formattedAddress"),
        "rating": place.get("rating"),
        "review_count": place.get("userRatingCount"),
        "maps_url": place.get("googleMapsUri"),
        "raw": place,
    }


def source_market(market: Market, memory, api_key: str | None = None, segments: list[str] | None = None,
                  districts: list[str] | None = None, max_pages: int = 3, session=requests) -> dict:
    """Sweep every (segment x district) query for a market. Returns counts."""
    api_key = api_key or os.environ.get("GOOGLE_PLACES_API_KEY")
    if not api_key:
        raise SourcingError("GOOGLE_PLACES_API_KEY is not set. STATUS: NOT YET CREATED.")
    stats = {"queries": 0, "seen": 0, "new": 0}
    for seg in segments or list(market.segments):
        query_word = market.segments[seg]["query"]
        for district in districts or market.districts:
            stats["queries"] += 1
            for place in places_search(f"{query_word} in {district}, {market.name}", api_key, max_pages, session):
                lead = place_to_lead(place, market, seg, district)
                if not lead or not lead["name"]:
                    continue
                stats["seen"] += 1
                stats["new"] += memory.upsert_lead(lead)
    return stats


def import_csv(path: Path | str, market: Market, memory, source: str = "csv") -> dict:
    stats = {"rows": 0, "new": 0}
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            row = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
            name = row.get("name") or row.get("business") or row.get("title")
            if not name:
                continue
            stats["rows"] += 1
            key = row.get("id") or row.get("phone") or row.get("website") or name
            lead = {
                "id": f"{source}:{re.sub(r'[^a-z0-9+]+', '-', key.lower())}",
                "market": market.id,
                "segment": row.get("segment") or row.get("category"),
                "district": row.get("district") or row.get("area"),
                "name": name,
                "phone": row.get("phone"),
                "email": row.get("email"),
                "website": row.get("website"),
                "address": row.get("address"),
                "rating": float(row["rating"]) if row.get("rating") else None,
                "review_count": int(float(row["reviews"])) if row.get("reviews") else None,
                "maps_url": row.get("maps_url"),
                "raw": row,
            }
            stats["new"] += memory.upsert_lead(lead)
    return stats


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
GENERIC_PREFIXES = ("info", "hello", "contact", "booking", "bookings", "reception", "admin", "salon", "enquiries")


def find_business_email(website: str, session=requests) -> str | None:
    """Fetch a business homepage and return a generic business inbox (info@, booking@ ...) if published.

    Only generic role addresses are returned — never personal ones — to stay on the B2B side of privacy law.
    """
    try:
        html = session.get(website, timeout=15, headers={"User-Agent": "Mozilla/5.0"}).text
    except Exception:
        return None
    for email in dict.fromkeys(m.lower() for m in EMAIL_RE.findall(html)):
        if email.split("@")[0] in GENERIC_PREFIXES and not email.endswith((".png", ".jpg", ".webp")):
            return email
    return None
