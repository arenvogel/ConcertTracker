"""Render matched events to HTML and ICS."""

import itertools
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from icalendar import Calendar, Event as IcsEvent
from jinja2 import Environment, FileSystemLoader

from config import OUTPUT_DIR, ROOT

# Where the "Email show details" button sends to.
EMAIL_TO = "julessofo@gmail.com"

env = Environment(
    loader=FileSystemLoader(str(ROOT / "templates")),
    # Always escape: the only template (index.html.j2) renders untrusted,
    # scraped event names. select_autoescape() keys off the file extension
    # and would return False for the ".j2" suffix, leaving output unescaped.
    autoescape=True,
)


def _month_key(ev: dict) -> str:
    return (ev.get("date") or "9999-12")[:7]


def _format_month(key: str) -> str:
    if key == "9999-12":
        return "Date TBD"
    return datetime.strptime(key, "%Y-%m").strftime("%B %Y")


def _parse_date(iso: str | None):
    """Parse an ISO 'YYYY-MM-DD' date, or None if missing/malformed."""
    if not iso:
        return None
    try:
        return datetime.strptime(iso, "%Y-%m-%d").date()
    except ValueError:
        return None


def _date_label(iso: str | None) -> dict:
    d = _parse_date(iso)
    if not d:
        return {"dow": "—", "day": "—"}
    return {"dow": d.strftime("%a"), "day": d.strftime("%-d %b")}


def _on_sale_label(raw: str | None) -> str | None:
    """Human-readable on-sale date from an ISO datetime (Ticketmaster's
    sales.public.startDateTime, e.g. '2025-03-14T15:00:00Z'). Returns None
    when unknown so the row can omit the line."""
    if not raw:
        return None
    text = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    on_sale = dt.date()
    if on_sale <= datetime.now().date():
        return "On sale now"
    return f"On sale {on_sale.strftime('%-d %b %Y')}"


def _email_url(ev: dict) -> str:
    """A mailto: link that pre-fills an email to EMAIL_TO with show details."""
    subject = f"Concert: {ev['headliner']} @ {ev['venue']}"
    if ev.get("date"):
        subject += f" — {_date_label(ev['date'])['day']}"

    lines = [ev["headliner"]]
    if ev.get("supports"):
        lines.append("with " + ", ".join(ev["supports"]))
    lines.append("")
    lines.append(f"Venue: {ev['venue']}")
    d = _parse_date(ev.get("date"))
    if d:
        when = d.strftime("%A, %-d %B %Y")
        if ev.get("time"):
            when += f" at {ev['time']}"
        lines.append(f"When: {when}")
    if ev.get("price_min") is not None:
        lines.append(f"From: ${ev['price_min']:.0f}")
    on_sale = _on_sale_label(ev.get("on_sale_at"))
    if on_sale:
        lines.append(f"Tickets: {on_sale}")
    if ev.get("url"):
        lines.append(f"Link: {ev['url']}")

    body = "\n".join(lines)
    return f"mailto:{EMAIL_TO}?subject={quote(subject)}&body={quote(body)}"


def render_html(events: list[dict], total_scanned: int, out_path: Path) -> None:
    ordered = sorted(events, key=lambda e: e.get("date") or "9999-12-31")
    for ev in ordered:
        ev["date_label"] = _date_label(ev.get("date"))
        ev["on_sale_label"] = _on_sale_label(ev.get("on_sale_at"))
        ev["email_url"] = _email_url(ev)

    grouped = [
        (_format_month(k), list(g))
        for k, g in itertools.groupby(ordered, key=_month_key)
    ]

    venues = sorted({ev["venue"] for ev in ordered})

    html = env.get_template("index.html.j2").render(
        events_by_month=grouped,
        venues=venues,
        total_events=total_scanned,
        matched_count=len(ordered),
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )
    out_path.write_text(html, encoding="utf-8")


def render_ics(events: list[dict], out_path: Path) -> None:
    cal = Calendar()
    cal.add("prodid", "-//DC Concerts//concerts//EN")
    cal.add("version", "2.0")
    cal.add("x-wr-calname", "DC Concerts")

    for ev in events:
        if not ev.get("date"):
            continue
        try:
            d = datetime.strptime(ev["date"], "%Y-%m-%d").date()
        except ValueError:
            continue

        entry = IcsEvent()
        match_names = ", ".join(m["name"] for m in ev.get("matches", []))
        summary = f"{ev['headliner']} @ {ev['venue']}"
        if match_names:
            summary += f" ({match_names})"
        entry.add("summary", summary)
        entry.add("dtstart", d)
        entry.add("dtend", d)
        entry.add("location", ev["venue"])
        desc_lines = []
        if ev.get("supports"):
            desc_lines.append("with " + ", ".join(ev["supports"]))
        if ev.get("url"):
            desc_lines.append(ev["url"])
        if desc_lines:
            entry.add("description", "\n".join(desc_lines))
        if ev.get("url"):
            entry.add("url", ev["url"])
        entry["uid"] = f"{ev.get('source','?')}-{ev.get('source_event_id','?')}@dcconcerts"
        cal.add_component(entry)

    out_path.write_bytes(cal.to_ical())


def write_outputs(events: list[dict], total_scanned: int) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    render_html(events, total_scanned, OUTPUT_DIR / "index.html")
    render_ics(events, OUTPUT_DIR / "concerts.ics")
