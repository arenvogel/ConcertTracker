"""Spotify client: refresh-token flow + liked-tracks artist extraction."""

import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE = "https://api.spotify.com/v1"


class SpotifyAuthError(RuntimeError):
    """The refresh token is missing, revoked, or expired: needs a re-login."""


def _get_access_token() -> str:
    refresh_token = os.environ.get("SPOTIFY_REFRESH_TOKEN")
    if not refresh_token:
        raise SpotifyAuthError(
            "SPOTIFY_REFRESH_TOKEN not set"
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
    if r.status_code in (400, 401):
        try:
            err = r.json()
        except ValueError:
            err = {}
        if err.get("error") in ("invalid_grant", "invalid_client"):
            raise SpotifyAuthError(
                err.get("error_description") or err.get("error")
            )
    if not r.ok:
        raise RuntimeError(f"Spotify token refresh failed ({r.status_code}): {r.text}")
    return r.json()["access_token"]


def _get_with_retry(url: str, headers: dict, attempts: int = 5) -> requests.Response:
    """GET with backoff on transient Spotify errors (429 / 5xx / network)."""
    for i in range(attempts):
        try:
            r = requests.get(url, headers=headers, timeout=30)
        except requests.RequestException:
            if i == attempts - 1:
                raise
        else:
            if r.status_code != 429 and r.status_code < 500:
                r.raise_for_status()
                return r
            if i == attempts - 1:
                r.raise_for_status()
            try:
                wait = int(float(r.headers.get("Retry-After") or 0))
            except ValueError:
                wait = 0
            if wait:
                time.sleep(min(wait, 60))
                continue
        time.sleep(2 ** i)
    raise RuntimeError("unreachable")


def fetch_liked_artists() -> set[str]:
    """Paginate through the user's saved tracks and return unique artist names."""
    token = _get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    artists: set[str] = set()
    url = f"{API_BASE}/me/tracks?limit=50"
    while url:
        r = _get_with_retry(url, headers)
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
