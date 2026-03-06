from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

import requests

from src.live.insight.models import KeywordConfig, RealtimeInsightConfig
from src.live.insight.openai_client import InsightModelResult
from src.live.insight.stage_processor import InsightStageProcessor
from src.live.mic import MicChunkProcessor, MicPublisher, build_mic_http_handler


def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


class _FakeClient:
    def transcribe_chunk(self, *, chunk_path: Path, stt_model: str, timeout_sec: float) -> str:
        return "hello"

    def analyze_text(
        self,
        *,
        analysis_model: str,
        keywords: KeywordConfig,
        current_text: str,
        context_text: str,
        timeout_sec: float,
    ) -> InsightModelResult:
        return InsightModelResult(
            important=False,
            summary="ok",
            context_summary="ok",
            matched_terms=[],
            reason="ok",
        )


class MicPipelineTests(unittest.TestCase):
    def test_mic_publisher_ffmpeg_command_contains_dshow(self) -> None:
        cmd = MicPublisher.build_ffmpeg_command(
            ffmpeg_bin="ffmpeg",
            device="Microphone (USB)",
            chunk_seconds=10,
            work_dir=Path("/tmp/work"),
        )
        self.assertIn("-f", cmd)
        self.assertIn("dshow", cmd)
        self.assertIn("audio=Microphone (USB)", cmd)
        self.assertIn("-segment_time", cmd)
        self.assertIn("10", cmd)

    def test_mic_http_auth_size_dedupe_and_processing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            cfg = RealtimeInsightConfig(
                enabled=True,
                chunk_seconds=10,
                stt_request_timeout_sec=8.0,
                stt_stage_timeout_sec=32.0,
                stt_retry_count=2,
                stt_retry_interval_sec=0.01,
                analysis_request_timeout_sec=15.0,
                analysis_stage_timeout_sec=60.0,
                analysis_retry_count=2,
                analysis_retry_interval_sec=0.01,
                context_recent_required=0,
                context_wait_timeout_sec_1=0.0,
                context_wait_timeout_sec_2=0.0,
                context_wait_timeout_sec=0.0,
                context_target_chunks=18,
                use_dual_context_wait=True,
                mic_chunk_max_bytes=32,
            )
            stage_processor = InsightStageProcessor(
                session_dir=base,
                config=cfg,
                keywords=KeywordConfig(),
                client=_FakeClient(),  # type: ignore[arg-type]
                log_fn=lambda _msg: None,
            )
            processor = MicChunkProcessor(
                stage_processor=stage_processor,
                chunk_dir=base / "_rt_chunks_mic",
                max_chunk_bytes=cfg.mic_chunk_max_bytes,
                log_fn=lambda _msg: None,
            )
            processor.start()

            server = ThreadingHTTPServer(
                ("127.0.0.1", 0),
                build_mic_http_handler(processor=processor, upload_token="token-1"),
            )
            thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True)
            thread.start()
            try:
                base_url = f"http://127.0.0.1:{server.server_port}"

                bad = requests.post(
                    f"{base_url}/api/mic/chunk",
                    data=b"1234",
                    headers={"X-Mic-Token": "bad", "X-Chunk-Name": "a.mp3"},
                    timeout=3,
                )
                self.assertEqual(bad.status_code, 401)

                too_large = requests.post(
                    f"{base_url}/api/mic/chunk",
                    data=b"x" * 64,
                    headers={"X-Mic-Token": "token-1", "X-Chunk-Name": "big.mp3"},
                    timeout=3,
                )
                self.assertEqual(too_large.status_code, 413)

                ok = requests.post(
                    f"{base_url}/api/mic/chunk",
                    data=b"abcd",
                    headers={"X-Mic-Token": "token-1", "X-Chunk-Name": "ok.mp3"},
                    timeout=3,
                )
                self.assertEqual(ok.status_code, 202)
                self.assertTrue(ok.json().get("accepted"))

                dup = requests.post(
                    f"{base_url}/api/mic/chunk",
                    data=b"abcd",
                    headers={"X-Mic-Token": "token-1", "X-Chunk-Name": "dup.mp3"},
                    timeout=3,
                )
                self.assertEqual(dup.status_code, 200)
                self.assertTrue(dup.json().get("duplicate"))

                deadline = time.time() + 3.0
                while time.time() < deadline:
                    metrics = requests.get(f"{base_url}/api/mic/metrics", timeout=3).json()
                    if int(metrics.get("processed_total", 0)) >= 1:
                        break
                    time.sleep(0.05)

                metrics = requests.get(f"{base_url}/api/mic/metrics", timeout=3).json()
                self.assertGreaterEqual(int(metrics.get("processed_total", 0)), 1)
                self.assertEqual(int(metrics.get("duplicate_total", 0)), 1)
                self.assertEqual(int(metrics.get("auth_failures", 0)), 1)
                self.assertEqual(int(metrics.get("too_large_total", 0)), 1)

                transcript_rows = _read_jsonl(base / "realtime_transcripts.jsonl")
                insight_rows = _read_jsonl(base / "realtime_insights.jsonl")
                self.assertEqual(len(transcript_rows), 1)
                self.assertEqual(len(insight_rows), 1)
                self.assertEqual(transcript_rows[0]["status"], "ok")
                self.assertEqual(insight_rows[0]["status"], "ok")
            finally:
                server.shutdown()
                server.server_close()
                processor.stop()


if __name__ == "__main__":
    unittest.main()
