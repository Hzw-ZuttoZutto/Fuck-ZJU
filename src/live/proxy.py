from __future__ import annotations

import re
import threading
import time
import urllib.parse
from dataclasses import dataclass
from http import HTTPStatus

import requests

from src.live.models import ProxyStats, StreamInfo


@dataclass
class _PlaylistCacheEntry:
    body: bytes
    cached_at: float


def rewrite_playlist_line(base_url: str, line: str) -> str:
    line = line.strip()
    if not line or line.startswith("#"):
        if line.startswith("#EXT-X-KEY:") and 'URI="' in line:

            def replace_uri(match: re.Match[str]) -> str:
                raw_uri = match.group(1)
                abs_uri = urllib.parse.urljoin(base_url, raw_uri)
                proxied = "/proxy/asset?u=" + urllib.parse.quote(abs_uri, safe="")
                return f'URI="{proxied}"'

            return re.sub(r'URI="([^"]+)"', replace_uri, line)
        return line

    abs_url = urllib.parse.urljoin(base_url, line)
    return "/proxy/asset?u=" + urllib.parse.quote(abs_url, safe="")


def is_allowed_upstream(upstream: str, allowed_suffixes: tuple[str, ...]) -> bool:
    parsed = urllib.parse.urlparse(upstream)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or not host:
        return False
    return any(host.endswith(suffix) for suffix in allowed_suffixes)


class ProxyEngine:
    def __init__(
        self,
        session: requests.Session,
        upstream_timeout: int,
        playlist_retries: int,
        asset_retries: int,
        stale_playlist_grace: float,
        allowed_suffixes: tuple[str, ...] = ("cmc.zju.edu.cn", "zju.edu.cn"),
    ) -> None:
        self.session = session
        self.upstream_timeout = upstream_timeout
        self.playlist_retries = max(0, playlist_retries)
        self.asset_retries = max(0, asset_retries)
        self.stale_playlist_grace = max(0.0, stale_playlist_grace)
        self.allowed_suffixes = allowed_suffixes

        self._lock = threading.Lock()
        self._stats = ProxyStats()
        self._playlist_cache: dict[str, _PlaylistCacheEntry] = {}

    def get_metrics(self) -> dict:
        now = time.time()
        with self._lock:
            cache_info = {
                role: {
                    "age_sec": round(now - item.cached_at, 3),
                    "size": len(item.body),
                    "cached_at_unix": item.cached_at,
                }
                for role, item in self._playlist_cache.items()
            }
            return {
                "proxy": self._stats.to_json_dict(),
                "playlist_cache": cache_info,
            }

    def _mark_playlist_request(self) -> None:
        with self._lock:
            self._stats.playlist_requests += 1

    def _mark_playlist_success(self, retried: bool) -> None:
        with self._lock:
            self._stats.consecutive_playlist_failures = 0
            if retried:
                self._stats.playlist_retry_successes += 1

    def _mark_playlist_failure(self) -> None:
        with self._lock:
            self._stats.playlist_failures += 1
            self._stats.consecutive_playlist_failures += 1

    def _mark_stale_playlist_hit(self) -> None:
        with self._lock:
            self._stats.playlist_stale_hits += 1

    def _mark_asset_request(self) -> None:
        with self._lock:
            self._stats.asset_requests += 1

    def _mark_asset_success(self, retried: bool) -> None:
        with self._lock:
            self._stats.consecutive_asset_failures = 0
            if retried:
                self._stats.asset_retry_successes += 1

    def _mark_asset_failure(self) -> None:
        with self._lock:
            self._stats.asset_failures += 1
            self._stats.consecutive_asset_failures += 1

    def proxy_playlist(self, handler, role: str, stream: StreamInfo | None) -> None:
        self._mark_playlist_request()

        if not stream or not stream.stream_m3u8:
            handler.send_error(HTTPStatus.NOT_FOUND, f"{role} stream not available")
            return

        attempts = self.playlist_retries + 1
        last_error: Exception | None = None

        for attempt in range(attempts):
            try:
                resp = self.session.get(stream.stream_m3u8, timeout=self.upstream_timeout)
                resp.raise_for_status()
                base_url = stream.stream_m3u8
                lines = resp.text.splitlines()
                rewritten = [rewrite_playlist_line(base_url, line) for line in lines]
                body_text = "\n".join(rewritten) + "\n"
                body = body_text.encode("utf-8")

                with self._lock:
                    self._playlist_cache[role] = _PlaylistCacheEntry(body=body, cached_at=time.time())
                self._mark_playlist_success(retried=(attempt > 0))

                handler.send_response(HTTPStatus.OK)
                handler.send_header("Content-Type", "application/vnd.apple.mpegurl")
                handler.send_header("Cache-Control", "no-store")
                handler.send_header("Content-Length", str(len(body)))
                handler.end_headers()
                handler.wfile.write(body)
                return
            except requests.RequestException as exc:
                last_error = exc
                continue

        self._mark_playlist_failure()

        with self._lock:
            cached = self._playlist_cache.get(role)

        if cached is not None and (time.time() - cached.cached_at) <= self.stale_playlist_grace:
            self._mark_stale_playlist_hit()
            handler.send_response(HTTPStatus.OK)
            handler.send_header("Content-Type", "application/vnd.apple.mpegurl")
            handler.send_header("Cache-Control", "no-store")
            handler.send_header("X-Stale-Playlist", "1")
            handler.send_header("Content-Length", str(len(cached.body)))
            handler.end_headers()
            handler.wfile.write(cached.body)
            return

        handler.send_error(HTTPStatus.BAD_GATEWAY, f"upstream m3u8 error: {last_error}")

    def proxy_asset(self, handler, upstream: str) -> None:
        self._mark_asset_request()

        if not upstream:
            handler.send_error(HTTPStatus.BAD_REQUEST, "missing url")
            return

        if not is_allowed_upstream(upstream, self.allowed_suffixes):
            handler.send_error(HTTPStatus.FORBIDDEN, "host not allowed")
            return

        attempts = self.asset_retries + 1
        last_error: Exception | None = None

        for attempt in range(attempts):
            upstream_resp = None
            try:
                upstream_resp = self.session.get(upstream, stream=True, timeout=self.upstream_timeout)
                upstream_resp.raise_for_status()

                content_type = upstream_resp.headers.get("Content-Type", "application/octet-stream")
                handler.send_response(HTTPStatus.OK)
                handler.send_header("Content-Type", content_type)
                handler.send_header("Cache-Control", "no-store")
                handler.end_headers()

                for chunk in upstream_resp.iter_content(chunk_size=64 * 1024):
                    if not chunk:
                        continue
                    handler.wfile.write(chunk)

                self._mark_asset_success(retried=(attempt > 0))
                return
            except requests.RequestException as exc:
                last_error = exc
                continue
            finally:
                if upstream_resp is not None:
                    upstream_resp.close()

        self._mark_asset_failure()
        handler.send_error(HTTPStatus.BAD_GATEWAY, f"upstream asset error: {last_error}")
