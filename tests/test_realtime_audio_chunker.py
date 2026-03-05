from __future__ import annotations

import signal
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.live.insight.audio_chunker import RealtimeAudioChunker


class _DummyProc:
    def __init__(self) -> None:
        self._stopped = False
        self.signal_sent = None
        self.killed = False

    def poll(self):
        return 0 if self._stopped else None

    def send_signal(self, sig) -> None:
        self.signal_sent = sig
        self._stopped = True

    def wait(self, timeout: float = 0.0) -> None:
        return

    def kill(self) -> None:
        self.killed = True
        self._stopped = True


class RealtimeAudioChunkerTests(unittest.TestCase):
    def test_start_builds_segment_command(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            proc = _DummyProc()
            with mock.patch("src.live.insight.audio_chunker.which", return_value="/usr/bin/ffmpeg"):
                chunker = RealtimeAudioChunker(chunk_dir=Path(td), chunk_seconds=10)
            with mock.patch("src.live.insight.audio_chunker.subprocess.Popen", return_value=proc) as popen:
                chunker.start("https://x/live.m3u8")

            args = popen.call_args[0][0]
            self.assertIn("-segment_time", args)
            self.assertIn("10", args)
            self.assertIn("chunk_%Y%m%d_%H%M%S.mp3", " ".join(args))
            self.assertEqual(chunker.active_url, "https://x/live.m3u8")

    def test_start_same_url_does_not_restart(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            proc = _DummyProc()
            with mock.patch("src.live.insight.audio_chunker.which", return_value="/usr/bin/ffmpeg"):
                chunker = RealtimeAudioChunker(chunk_dir=Path(td), chunk_seconds=10)
            with mock.patch("src.live.insight.audio_chunker.subprocess.Popen", return_value=proc) as popen:
                chunker.start("https://x/live.m3u8")
                chunker.start("https://x/live.m3u8")
            self.assertEqual(popen.call_count, 1)

    def test_stop_sends_sigint(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            proc = _DummyProc()
            with mock.patch("src.live.insight.audio_chunker.which", return_value="/usr/bin/ffmpeg"):
                chunker = RealtimeAudioChunker(chunk_dir=Path(td), chunk_seconds=10)
            with mock.patch("src.live.insight.audio_chunker.subprocess.Popen", return_value=proc):
                chunker.start("https://x/live.m3u8")
            chunker.stop()
            self.assertEqual(proc.signal_sent, signal.SIGINT)


if __name__ == "__main__":
    unittest.main()
