"""Slack alerts for pipeline failures. No-op when SLACK_BOT_TOKEN is unset
(e.g. local runs), so it never masks the real error."""

import os

import requests

REAUTH_COMMAND = "concert-reauth"


def run_url() -> str | None:
    server = os.environ.get("GITHUB_SERVER_URL")
    repo = os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")
    if server and repo and run_id:
        return f"{server}/{repo}/actions/runs/{run_id}"
    return None


def post_slack(text: str) -> bool:
    token = os.environ.get("SLACK_BOT_TOKEN", "").strip()
    channel = os.environ.get("SLACK_CHANNEL", "").strip()
    if not token or not channel:
        print("  (Slack alert skipped: SLACK_BOT_TOKEN/SLACK_CHANNEL not set)")
        return False
    try:
        r = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {token}"},
            json={"channel": channel, "text": text, "unfurl_links": False},
            timeout=15,
        )
        ok = r.ok and r.json().get("ok")
        if not ok:
            print(f"  (Slack alert failed: {r.text[:200]})")
        return bool(ok)
    except (requests.RequestException, ValueError) as e:
        print(f"  (Slack alert failed: {e})")
        return False


def spotify_reauth_message(detail: str) -> str:
    link = run_url()
    lines = [
        ":warning: *Concert Tracker needs a Spotify re-login*",
        f"Spotify auth failed ({detail}), so the site isn't refreshing.",
        f"*Fix (~30 sec):* open Terminal on your Mac and run `{REAUTH_COMMAND}`, then approve in the browser. "
        "It updates the GitHub secret and re-runs the refresh for you.",
    ]
    if link:
        lines.append(f"<{link}|Failed run>")
    lines.append("_Repeats daily until fixed._")
    return "\n".join(lines)


def generic_failure_message(error: str) -> str:
    link = run_url()
    msg = f":x: *Concert Tracker refresh failed*\n`{error[:300]}`"
    if link:
        msg += f"\n<{link}|View run logs>"
    return msg
