"""Ticketmaster Discovery API source."""

import os
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

from config import HORIZON_DAYS, TICKETMASTER_VENUES

load_dotenv()

BASE = "https://app.ticketmaster.com/discovery/v2"


def _api_key() -> str:
    return os.environ["TICKETMASTER_API_KEY"]


def _fetch_events_for_venue(venue_id: str) -> list[dict]:
    events: list[dict] = []
    page = 0
    now = datetime.now(timezone.utc)
    start = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    end = (now + timedelta(days=HORIZON_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    while True:
        r = requests.get(
            f"{BASE}/events.json",
            params={
                "venueId": venue_id,
                "classificationName": "music",
                "startDateTime": start,
                "endDateTime": end,
                "size": 100,
                "page": page,
                "apikey": _api_key(),
            },
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        events.extend(data.get("_embedded", {}).get("events", []))
        pagination = data.get("page", {})
        if page + 1 >= pagination.get("totalPages", 0):
            break
        page += 1
    return events


def _normalize(ev: dict, venue_name: str) -> dict:
    attractions = ev.get("_embedded", {}).get("attractions", [])
    artists = [a["name"] for a in attractions if a.get("name")]
    if not artists:
        artists = [ev.get("name", "Unknown")]

    start = ev.get("dates", {}).get("start", {})
    price_ranges = ev.get("priceRanges", [])
    price_min = min((p.get("min") for p in price_ranges if p.get("min") is not None), default=None)

    return {
        "source": "ticketmaster",
        "source_event_id": ev.get("id"),
        "venue": venue_name,
        "headliner": artists[0],
        "supports": artists[1:],
        "date": start.get("localDate"),
        "time": start.get("localTime"),
        "url": ev.get("url"),
        "price_min": price_min,
        "on_sale_at": ev.get("sales", {}).get("public", {}).get("startDateTime"),
    }


def fetch_events() -> list[dict]:
    all_events: list[dict] = []
    for name, venue_id in TICKETMASTER_VENUES:
        try:
            raw = _fetch_events_for_venue(venue_id)
            for ev in raw:
                all_events.append(_normalize(ev, name))
            print(f"[ticketmaster] {name}: {len(raw)} events")
        except Exception as e:
            print(f"[ticketmaster] {name} failed: {e}")
    return all_events


if __name__ == "__main__":
    events = fetch_events()
    print(f"\nTotal: {len(events)} events")
    for e in sorted(events, key=lambda x: x["date"] or "")[:10]:
        print(f"  {e['date']} @ {e['venue']}: {e['headliner']}")
