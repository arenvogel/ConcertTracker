"""Artist name normalization and event-to-liked-artist matching."""

import re
import unicodedata


def normalize(name: str) -> str:
    if not name:
        return ""
    s = name.lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"^the\s+", "", s)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


_SPLIT_RE = re.compile(
    r"\s*(?:"
    r"\bwith\b|\bfeat\.?\b|\bft\.?\b|\bw/\b|\bvs\.?\b|\band\b|"
    r"&|,|/|\+|\s-\s|:"
    r")\s*",
    re.IGNORECASE,
)


def split_artists(text: str) -> list[str]:
    if not text:
        return []
    return [p.strip() for p in _SPLIT_RE.split(text) if p.strip()]


def _match_string(raw: str, liked_norm: set[str]) -> str | None:
    """Return the matched liked-artist display key, or None.
    Tries the whole string first, then splits on common delimiters."""
    if not raw:
        return None
    whole = normalize(raw)
    if whole in liked_norm:
        return whole
    for part in split_artists(raw):
        n = normalize(part)
        if n in liked_norm:
            return n
    return None


def match_events(events: list[dict], liked_artists: set[str]) -> list[dict]:
    """Return events that have at least one matching performer.
    Each returned event is annotated with a 'matches' list of
    {name, role, normalized} dicts."""
    liked_norm = {normalize(a): a for a in liked_artists}
    matched: list[dict] = []
    for ev in events:
        matches: list[dict] = []
        headliner_norm = _match_string(ev.get("headliner", ""), set(liked_norm))
        if headliner_norm:
            matches.append(
                {"name": liked_norm[headliner_norm], "role": "headliner", "normalized": headliner_norm}
            )
        for support in ev.get("supports", []) or []:
            support_norm = _match_string(support, set(liked_norm))
            if support_norm:
                matches.append(
                    {"name": liked_norm[support_norm], "role": "support", "normalized": support_norm}
                )
        seen: set[str] = set()
        deduped = [m for m in matches if not (m["normalized"] in seen or seen.add(m["normalized"]))]
        if deduped:
            ev = dict(ev)
            ev["matches"] = deduped
            matched.append(ev)
    return matched
