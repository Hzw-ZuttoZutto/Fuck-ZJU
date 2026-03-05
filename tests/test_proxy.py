from __future__ import annotations

import io
import unittest

import requests

from src.live.models import StreamInfo
from src.live.proxy import ProxyEngine, is_allowed_upstream, rewrite_playlist_line


class _Handler:
    def __init__(self) -> None:
        self.status = None
        self.headers = {}
        self.error = None
        self.wfile = io.BytesIO()

    def send_response(self, status) -> None:
        self.status = int(status)

    def send_header(self, key: str, value: str) -> None:
        self.headers[key] = value

    def end_headers(self) -> None:
        return

    def send_error(self, status, message: str = "") -> None:
        self.status = int(status)
        self.error = message


class _Resp:
    def __init__(self, text: str = "", content_type: str = "application/octet-stream") -> None:
        self.text = text
        self.headers = {"Content-Type": content_type}

    def raise_for_status(self) -> None:
        return

    def iter_content(self, chunk_size: int = 65536):
        yield b"a"
        yield b"b"

    def close(self) -> None:
        return


class _Session:
    def __init__(self, sequence):
        self.sequence = list(sequence)

    def get(self, *args, **kwargs):
        if not self.sequence:
            raise RuntimeError("no more responses")
        item = self.sequence.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class ProxyTests(unittest.TestCase):
    def test_rewrite_playlist_line(self) -> None:
        out = rewrite_playlist_line("https://a.zju.edu.cn/live/index.m3u8", "seg01.ts")
        self.assertIn("/proxy/asset?u=", out)

        key = rewrite_playlist_line(
            "https://a.zju.edu.cn/live/index.m3u8",
            '#EXT-X-KEY:METHOD=AES-128,URI="key.key"',
        )
        self.assertIn("/proxy/asset?u=", key)

    def test_is_allowed_upstream(self) -> None:
        self.assertTrue(is_allowed_upstream("https://x.zju.edu.cn/a.ts", ("zju.edu.cn",)))
        self.assertFalse(is_allowed_upstream("https://evil.com/a.ts", ("zju.edu.cn",)))

    def test_playlist_stale_fallback(self) -> None:
        stream = StreamInfo(
            type=3,
            type_name="teacher",
            id="1",
            sub_id="2",
            source_id="3",
            stream_id="4",
            stream_name="t",
            video_track="1",
            video_track_on=True,
            voice_track="1",
            voice_track_on=True,
            is_gortc=None,
            stream_m3u8="https://x.zju.edu.cn/index.m3u8",
            stream_play="",
            stream_m3u8_meta={},
            stream_play_meta={},
        )

        session = _Session([
            _Resp("#EXTM3U\nseg.ts\n", "application/vnd.apple.mpegurl"),
            requests.RequestException("err1"),
            requests.RequestException("err2"),
        ])
        engine = ProxyEngine(
            session=session,
            upstream_timeout=5,
            playlist_retries=1,
            asset_retries=1,
            stale_playlist_grace=60,
            allowed_suffixes=("zju.edu.cn",),
        )

        h1 = _Handler()
        engine.proxy_playlist(h1, "teacher", stream)
        self.assertEqual(h1.status, 200)
        self.assertTrue(h1.wfile.getvalue())

        h2 = _Handler()
        engine.proxy_playlist(h2, "teacher", stream)
        self.assertEqual(h2.status, 200)
        self.assertEqual(h2.headers.get("X-Stale-Playlist"), "1")

    def test_asset_retry_success(self) -> None:
        session = _Session([
            requests.RequestException("first fail"),
            _Resp(content_type="video/mp2t"),
        ])
        engine = ProxyEngine(
            session=session,
            upstream_timeout=5,
            playlist_retries=1,
            asset_retries=2,
            stale_playlist_grace=15,
            allowed_suffixes=("zju.edu.cn",),
        )

        handler = _Handler()
        engine.proxy_asset(handler, "https://x.zju.edu.cn/seg.ts")
        self.assertEqual(handler.status, 200)
        self.assertEqual(handler.wfile.getvalue(), b"ab")


if __name__ == "__main__":
    unittest.main()
