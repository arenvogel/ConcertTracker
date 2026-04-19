"""Render matched events to HTML and ICS."""

import itertools
from datetime import datetime
from pathlib import Path

from icalendar import Calendar, Event as IcsEvent
from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import OUTPUT_DIR, ROOT

env = Environment(
    loader=FileSystemLoader(str(ROOT / "templates")),
    autoescape=select_autoescape(["html"]),
)


def _month_key(ev: dict) -> str:
    return (ev.get("date") or "9999-12")[:7]


def _format_month(key: str) -> str:
    if key == "9999-12":
        return "Date TBD"
    return datetime.strptime(key, "%Y-%m").strftime("%B %Y")


def _date_label(iso: str | None) -> dict:
    if not iso:
        return {"dow": "—", "day": "—"}
    d = datetime.strptime(iso, "%Y-%m-%d").date()
    return {"dow": d.strftime("%a"), "day": d.strftime("%-d %b")}


def render_html(events: list[dict], total_scanned: int, out_path: Path) -> None:
    ordered = sorted(events, key=lambda e: e.get("date") or "9999-12-31")
    for ev in ordered:
        ev["date_label"] = _date_label(ev.get("date"))

    grouped = [
        (_format_month(k), list(g))
        for k, g in itertools.groupby(ordered, key=_month_key)
    ]

    html = env.get_template("index.html.j2").render(
        events_by_month=grouped,
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
