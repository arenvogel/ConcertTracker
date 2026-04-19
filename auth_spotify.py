"""One-time Spotify OAuth flow. Run locally, then copy the printed refresh
token into .env (SPOTIFY_REFRESH_TOKEN) and into GitHub Actions secrets."""

import os
from pathlib import Path

from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

CACHE_PATH = Path(__file__).parent / ".cache-spotify"

oauth = SpotifyOAuth(
    client_id=os.environ["SPOTIFY_CLIENT_ID"],
    client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
    redirect_uri=os.environ["SPOTIFY_REDIRECT_URI"],
    scope="user-library-read",
    cache_path=str(CACHE_PATH),
    open_browser=True,
)

token_info = oauth.get_access_token(as_dict=True)

print()
print("=" * 70)
print("SPOTIFY_REFRESH_TOKEN:")
print(token_info["refresh_token"])
print("=" * 70)
print()
print("Next steps:")
print("  1. Paste the token above into .env as SPOTIFY_REFRESH_TOKEN")
print("  2. Add it to GitHub Actions secrets when the repo is set up")
