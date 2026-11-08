"""Orchestrator: fetch → match → render. Entrypoint for GitHub Actions."""

import sys
from pathlib import Path

from matcher import match_events, normalize
from notify import generic_failure_message, post_slack, spotify_reauth_message
from render import write_outputs
from sources import black_cat, ticketmaster
from spotify_client import SpotifyAuthError, fetch_liked_artists

# Tells the workflow's fallback alert step that we already posted to Slack.
ALERT_MARKER = Path(__file__).parent / ".alert_sent"


def dedupe(events: list[dict]) -> list[dict]:
    """Drop repeats: venues with two Ticketmaster IDs return the same event
    twice, and Ticketmaster sometimes lists one show under two event IDs."""
    seen: set = set()
    out: list[dict] = []
    for ev in events:
        keys = {("id", ev.get("source"), ev.get("source_event_id")),
                ("show", normalize(ev.get("venue", "")), ev.get("date"),
                 normalize(ev.get("headliner", "")))}
        if keys & seen:
            continue
        seen |= keys
        out.append(ev)
    return out


def run() -> None:
    print("Fetching liked artists from Spotify...")
    liked = fetch_liked_artists()
    print(f"  {len(liked)} liked artists")

    print("Fetching events...")
    events = ticketmaster.fetch_events() + black_cat.fetch_events()
    raw_count = len(events)
    events = dedupe(events)
    print(f"  {len(events)} total events ({raw_count - len(events)} duplicates dropped)")

    print("Matching...")
    matched = match_events(events, liked)
    print(f"  {len(matched)} matched events")

    print("Rendering output...")
    write_outputs(matched, total_scanned=len(events))
    print("Done.")


def main() -> None:
    try:
        run()
    except SpotifyAuthError as e:
        print(f"Spotify auth failed: {e}", file=sys.stderr)
        if post_slack(spotify_reauth_message(str(e))):
            ALERT_MARKER.touch()
        raise
    except Exception as e:
        if post_slack(generic_failure_message(f"{type(e).__name__}: {e}")):
            ALERT_MARKER.touch()
        raise


if __name__ == "__main__":
    main()
