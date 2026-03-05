from __future__ import annotations

import json
import threading
import time
import unittest
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests

from src.live.models import StreamInfo
from src.live.proxy import ProxyEngine
from src.live.server import WatchRequestHandler


class _UpstreamHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/live/index.m3u8":
            body = b"#EXTM3U\n#EXTINF:2.0,\nseg.ts\n"
            self.send_response(200)
            self.send_header("Content-Type", "application/vnd.apple.mpegurl")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/live/seg.ts":
            body = b"SEGMENT"
            self.send_response(200)
            self.send_header("Content-Type", "video/mp2t")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, fmt, *args):
        return


class _FakePoller:
    def __init__(self, stream_url: str):
        self.stream_url = stream_url

    def get_snapshot(self):
        stream = StreamInfo(
            type=3,
            type_name="teacher",
            id="1",
            sub_id="2",
            source_id="3",
            stream_id="4",
            stream_name="teacher",
            video_track="1",
            video_track_on=True,
            voice_track="1",
            voice_track_on=True,
            is_gortc=None,
            stream_m3u8=self.stream_url,
            stream_play="",
            stream_m3u8_meta={},
            stream_play_meta={},
        )

        class Snap:
            updated_at_utc = "2026-01-01T00:00:00+00:00"
            success = True
            result_err = 0
            result_err_msg = ""
            error = ""
            streams = {"teacher": stream, "ppt": stream}
            raw_streams = []
            stream_count = 1

            def to_json_dict(self):
                return {
                    "updated_at_utc": self.updated_at_utc,
                    "success": self.success,
                    "result_err": self.result_err,
                    "result_err_msg": self.result_err_msg,
                    "error": self.error,
                    "stream_count": self.stream_count,
                    "streams": {"teacher": {}},
                    "raw_streams": [],
                }

        return Snap()

    def get_metrics(self):
        return {"poll_total": 1, "poll_failures": 0, "consecutive_poll_failures": 0}


class ServerIntegrationTests(unittest.TestCase):
    def test_proxy_and_metrics_endpoints(self) -> None:
        upstream = ThreadingHTTPServer(("127.0.0.1", 0), _UpstreamHandler)
        upstream_port = upstream.server_address[1]
        t1 = threading.Thread(target=upstream.serve_forever, daemon=True)
        t1.start()

        stream_url = f"http://127.0.0.1:{upstream_port}/live/index.m3u8"
        poller = _FakePoller(stream_url)
        proxy_engine = ProxyEngine(
            session=requests.Session(),
            upstream_timeout=5,
            playlist_retries=1,
            asset_retries=1,
            stale_playlist_grace=10,
            allowed_suffixes=("127.0.0.1",),
        )

        handler_cls = type(
            "THandler",
            (WatchRequestHandler,),
            {
                "poller": poller,
                "proxy_engine": proxy_engine,
                "course_id": 1,
                "sub_id": 2,
                "poll_interval": 3.0,
                "hls_js": "var Hls = function(){};",
                "hls_max_buffer": 20,
            },
        )

        server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
        server_port = server.server_address[1]
        t2 = threading.Thread(target=server.serve_forever, daemon=True)
        t2.start()

        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{server_port}/api/metrics") as resp:
                metrics = json.loads(resp.read().decode("utf-8"))
                self.assertIn("poller", metrics)
                self.assertIn("proxy", metrics)

            with urllib.request.urlopen(
                f"http://127.0.0.1:{server_port}/proxy/m3u8?role=teacher"
            ) as resp:
                text = resp.read().decode("utf-8")
                self.assertIn("/proxy/asset?u=", text)

            encoded = urllib.parse.quote(
                f"http://127.0.0.1:{upstream_port}/live/seg.ts", safe=""
            )
            with urllib.request.urlopen(
                f"http://127.0.0.1:{server_port}/proxy/asset?u={encoded}"
            ) as resp:
                body = resp.read()
                self.assertEqual(body, b"SEGMENT")
        finally:
            server.shutdown()
            server.server_close()
            upstream.shutdown()
            upstream.server_close()
            time.sleep(0.05)


if __name__ == "__main__":
    unittest.main()
