"""Orchestrator: fetch → match → render. Entrypoint for GitHub Actions."""

from matcher import match_events
from render import write_outputs
from sources import black_cat, ticketmaster
from spotify_client import fetch_liked_artists


def main() -> None:
    print("Fetching liked artists from Spotify...")
    liked = fetch_liked_artists()
    print(f"  {len(liked)} liked artists")

    print("Fetching events...")
    events = ticketmaster.fetch_events() + black_cat.fetch_events()
    print(f"  {len(events)} total events")

    print("Matching...")
    matched = match_events(events, liked)
    print(f"  {len(matched)} matched events")

    print("Rendering output...")
    write_outputs(matched, total_scanned=len(events))
    print("Done.")


if __name__ == "__main__":
    main()
