"""Spotify client: refresh-token flow + liked-tracks artist extraction."""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE = "https://api.spotify.com/v1"


def _get_access_token() -> str:
    refresh_token = os.environ.get("SPOTIFY_REFRESH_TOKEN")
    if not refresh_token:
        raise RuntimeError(
            "SPOTIFY_REFRESH_TOKEN not set. Run `python auth_spotify.py` first."
        )
    r = requests.post(
        TOKEN_URL,
        data={"grant_type": "refresh_token", "refresh_token": refresh_token.strip()},
        auth=(
            os.environ["SPOTIFY_CLIENT_ID"].strip(),
            os.environ["SPOTIFY_CLIENT_SECRET"].strip(),
        ),
        timeout=15,
    )
    if not r.ok:
        raise RuntimeError(f"Spotify token refresh failed ({r.status_code}): {r.text}")
    return r.json()["access_token"]


def fetch_liked_artists() -> set[str]:
    """Paginate through the user's saved tracks and return unique artist names."""
    token = _get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    artists: set[str] = set()
    url = f"{API_BASE}/me/tracks?limit=50"
    while url:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        for item in data["items"]:
            for artist in item["track"]["artists"]:
                artists.add(artist["name"])
        url = data.get("next")
    return artists


if __name__ == "__main__":
    found = fetch_liked_artists()
    print(f"Found {len(found)} unique artists in liked tracks")
    for name in sorted(found):
        print(f"  {name}")
