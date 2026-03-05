from __future__ import annotations

import urllib.parse
from datetime import datetime, timezone
from typing import Optional


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def to_int_or_none(value: object) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def parse_track_flag(value: object) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value

    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off", ""}:
        return False
    return None


def summarize_stream_url(url: str) -> dict:
    if not url:
        return {
            "present": False,
            "host": "",
            "path": "",
            "query_keys": [],
            "has_auth_key": False,
            "auth_key_expire_at_utc": "",
            "redacted_url": "",
        }

    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    query_keys = sorted(query.keys())

    auth_key_expire_at_utc = ""
    if "auth_key" in query and query["auth_key"]:
        auth_key = query["auth_key"][0]
        first_segment = auth_key.split("-", 1)[0]
        if first_segment.isdigit():
            ts = int(first_segment)
            auth_key_expire_at_utc = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()

    redacted_query = "&".join(f"{k}=***" for k in query_keys)
    redacted_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    if redacted_query:
        redacted_url += f"?{redacted_query}"

    return {
        "present": True,
        "host": parsed.netloc,
        "path": parsed.path,
        "query_keys": query_keys,
        "has_auth_key": "auth_key" in query,
        "auth_key_expire_at_utc": auth_key_expire_at_utc,
        "redacted_url": redacted_url,
    }


def html_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )
