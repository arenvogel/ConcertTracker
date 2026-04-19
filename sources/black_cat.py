"""Black Cat (independent, not on Ticketmaster). Scrape /schedule.html."""

from datetime import date, datetime

import requests
from bs4 import BeautifulSoup

URL = "https://blackcatdc.com/schedule.html"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


def _parse_date(text: str) -> str | None:
    """Parse 'Monday April 20' → ISO date. Year is inferred: if month/day
    is before today, it must be next year."""
    today = date.today()
    for fmt in ("%A %B %d", "%a %B %d"):
        try:
            dt = datetime.strptime(text.strip(), fmt).date()
            year = today.year
            candidate = dt.replace(year=year)
            if candidate < today:
                candidate = dt.replace(year=year + 1)
            return candidate.isoformat()
        except ValueError:
            continue
    return None


def _normalize(show) -> dict | None:
    headline_el = show.select_one(".headline")
    date_el = show.select_one(".date")
    if not headline_el or not date_el:
        return None

    headliner = headline_el.get_text(strip=True)
    event_date = _parse_date(date_el.get_text(strip=True))
    if not event_date:
        return None

    supports = [s.get_text(strip=True) for s in show.select(".support")]

    event_link = headline_el.select_one("a")
    event_url = event_link.get("href") if event_link else None

    ticket_link = show.select_one("a[href*='etix'], a[href*='ticket']")
    ticket_url = ticket_link.get("href") if ticket_link else event_url

    return {
        "source": "black_cat",
        "source_event_id": event_url,
        "venue": "Black Cat",
        "headliner": headliner,
        "supports": supports,
        "date": event_date,
        "time": None,
        "url": ticket_url,
        "price_min": None,
        "on_sale_at": None,
    }


def fetch_events() -> list[dict]:
    try:
        r = requests.get(URL, headers=HEADERS, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"[black_cat] fetch failed: {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    events: list[dict] = []
    for show in soup.select(".show"):
        try:
            ev = _normalize(show)
            if ev:
                events.append(ev)
        except Exception as e:
            print(f"[black_cat] skip item: {e}")
    print(f"[black_cat] Black Cat: {len(events)} events")
    return events


if __name__ == "__main__":
    events = fetch_events()
    for e in sorted(events, key=lambda x: x["date"])[:15]:
        supports = f" (+{len(e['supports'])})" if e['supports'] else ""
        print(f"  {e['date']}: {e['headliner']}{supports}")
