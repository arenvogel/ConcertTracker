"""One-command Spotify re-login for ConcertTracker (stdlib only, no pip needed).

    python3 auth_spotify.py          # or just `concert-reauth`

1. Reads SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET from .env (prompts and saves
   them if missing).
2. Opens the Spotify consent page and catches the redirect on 127.0.0.1:8888.
3. Exchanges the code for a refresh token and verifies it works.
4. Saves it to .env, updates the GitHub Actions secret, triggers the refresh
   workflow, and watches it to completion.

Flags: --no-github  only print/save the token, skip gh steps.
"""

import base64
import getpass
import http.server
import json
import secrets
import subprocess
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).parent
ENV_PATH = ROOT / ".env"
REPO = "arenvogel/ConcertTracker"
WORKFLOW = "Refresh concerts"
DEFAULT_REDIRECT = "http://127.0.0.1:8888/callback"
SCOPE = "user-library-read"
TOKEN_URL = "https://accounts.spotify.com/api/token"
TIMEOUT_SECONDS = 300


# ---------- .env helpers ----------

def read_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip().removeprefix("export ").strip() if hasattr(str, "removeprefix") else k.strip()
            env[k] = v.strip().strip('"').strip("'")
    return env


def write_env_value(key: str, value: str) -> None:
    lines = ENV_PATH.read_text().splitlines() if ENV_PATH.exists() else []
    out, found = [], False
    for line in lines:
        if line.split("=", 1)[0].strip() == key:
            out.append(f"{key}={value}")
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f"{key}={value}")
    ENV_PATH.write_text("\n".join(out) + "\n")
    ENV_PATH.chmod(0o600)


def ensure_credentials(env: dict[str, str]) -> tuple[str, str, str]:
    cid = env.get("SPOTIFY_CLIENT_ID", "")
    secret = env.get("SPOTIFY_CLIENT_SECRET", "")
    if not cid:
        cid = input("Spotify Client ID: ").strip()
        if cid:
            write_env_value("SPOTIFY_CLIENT_ID", cid)
    if not secret:
        secret = getpass.getpass("Spotify Client Secret (hidden): ").strip()
        if secret:
            write_env_value("SPOTIFY_CLIENT_SECRET", secret)
    redirect = env.get("SPOTIFY_REDIRECT_URI") or DEFAULT_REDIRECT
    if not cid or not secret:
        sys.exit("Client ID and secret are required (Spotify Developer Dashboard → app → Settings).")
    return cid, secret, redirect


# ---------- OAuth ----------

def token_request(cid: str, secret: str, data: dict) -> dict:
    basic = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    req = urllib.request.Request(
        TOKEN_URL,
        data=urllib.parse.urlencode(data).encode(),
        headers={"Authorization": f"Basic {basic}",
                 "Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"Spotify token request failed ({e.code}): {e.read().decode()[:300]}")


def get_auth_code(cid: str, redirect: str) -> str:
    parsed = urllib.parse.urlparse(redirect)
    host, port, path = parsed.hostname, parsed.port or 80, parsed.path
    state = secrets.token_urlsafe(16)
    result: dict[str, str] = {}
    done = threading.Event()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            if u.path != path:
                self.send_response(404); self.end_headers(); return
            q = urllib.parse.parse_qs(u.query)
            if q.get("state", [""])[0] != state:
                result["error"] = "state mismatch"
            elif "error" in q:
                result["error"] = q["error"][0]
            else:
                result["code"] = q.get("code", [""])[0]
            ok = "code" in result
            body = ("<h2>Spotify connected. You can close this tab.</h2>" if ok
                    else f"<h2>Spotify login failed: {result.get('error')}</h2>")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode())
            done.set()

        def log_message(self, *args):
            pass

    try:
        server = http.server.HTTPServer((host, port), Handler)
    except OSError as e:
        sys.exit(f"Can't listen on {host}:{port} ({e}). Close whatever is using that port and retry.")
    threading.Thread(target=server.serve_forever, daemon=True).start()

    url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode({
        "client_id": cid,
        "response_type": "code",
        "redirect_uri": redirect,
        "scope": SCOPE,
        "state": state,
        "show_dialog": "true",
    })
    print("Opening Spotify login in your browser...")
    print(f"(If it doesn't open, visit:\n  {url}\n)")
    webbrowser.open(url)

    got = done.wait(TIMEOUT_SECONDS)
    server.shutdown()
    server.server_close()
    if not got:
        sys.exit("Timed out waiting for Spotify login.")
    if "code" not in result:
        hint = ""
        if result.get("error") == "invalid_client":
            hint = " Check the client ID/secret in .env."
        sys.exit(f"Spotify login failed: {result.get('error')}.{hint}")
    return result["code"]


# ---------- GitHub ----------

def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, text=True, **kw)


def push_to_github(refresh_token: str) -> None:
    if run(["gh", "auth", "status"], capture_output=True).returncode != 0:
        print("gh CLI isn't logged in. Run `gh auth login`, then re-run this script.")
        print("Your new token is saved in .env, so you can also set it by hand:")
        print(f"  gh secret set SPOTIFY_REFRESH_TOKEN -R {REPO}")
        sys.exit(1)

    r = run(["gh", "secret", "set", "SPOTIFY_REFRESH_TOKEN", "-R", REPO],
            input=refresh_token, capture_output=True)
    if r.returncode != 0:
        sys.exit(f"Failed to update GitHub secret: {r.stderr.strip()}")
    print("✓ GitHub secret SPOTIFY_REFRESH_TOKEN updated")

    r = run(["gh", "workflow", "run", WORKFLOW, "-R", REPO], capture_output=True)
    if r.returncode != 0:
        print(f"Couldn't trigger the workflow ({r.stderr.strip()}). It will run on its daily schedule.")
        return
    print(f"✓ Triggered '{WORKFLOW}'. Waiting for it to start...")

    import time
    run_id = None
    for _ in range(15):
        time.sleep(3)
        r = run(["gh", "run", "list", "-R", REPO, "-w", WORKFLOW, "-e", "workflow_dispatch",
                 "-L", "1", "--json", "databaseId,status"], capture_output=True)
        try:
            runs = json.loads(r.stdout or "[]")
        except json.JSONDecodeError:
            runs = []
        if runs and runs[0]["status"] != "completed":
            run_id = str(runs[0]["databaseId"])
            break
    if not run_id:
        print(f"Run didn't show up yet. Check: https://github.com/{REPO}/actions")
        return
    r = run(["gh", "run", "watch", run_id, "-R", REPO, "--exit-status", "--interval", "5"],
            stdout=subprocess.DEVNULL)
    if r.returncode == 0:
        print("✓ Refresh succeeded. Site is updating: https://arenvogel.github.io/ConcertTracker/")
    else:
        print(f"✗ Refresh run failed. Logs: https://github.com/{REPO}/actions/runs/{run_id}")
        sys.exit(1)


# ---------- main ----------

def main() -> None:
    if any(a in ("-h", "--help") for a in sys.argv[1:]):
        print(__doc__)
        return
    unknown = [a for a in sys.argv[1:] if a != "--no-github"]
    if unknown:
        sys.exit(f"Unknown option(s): {' '.join(unknown)}. Try --help.")
    cid, secret, redirect = ensure_credentials(read_env())
    code = get_auth_code(cid, redirect)
    tokens = token_request(cid, secret, {
        "grant_type": "authorization_code", "code": code, "redirect_uri": redirect,
    })
    refresh = tokens.get("refresh_token")
    if not refresh:
        sys.exit(f"Spotify didn't return a refresh token: {tokens}")

    # Sanity check: the new token must refresh successfully.
    token_request(cid, secret, {"grant_type": "refresh_token", "refresh_token": refresh})
    write_env_value("SPOTIFY_REFRESH_TOKEN", refresh)
    print("✓ New Spotify refresh token verified and saved to .env")

    if "--no-github" in sys.argv:
        return
    push_to_github(refresh)


if __name__ == "__main__":
    main()
