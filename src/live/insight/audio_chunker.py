from __future__ import annotations

import signal
import subprocess
from pathlib import Path
from shutil import which


class RealtimeAudioChunker:
    def __init__(self, *, chunk_dir: Path, chunk_seconds: int) -> None:
        self.chunk_dir = chunk_dir
        self.chunk_seconds = max(2, int(chunk_seconds))
        self.ffmpeg = which("ffmpeg") or ""
        self._proc: subprocess.Popen | None = None
        self._active_url = ""

    def ensure_available(self) -> bool:
        return bool(self.ffmpeg)

    @property
    def active_url(self) -> str:
        return self._active_url

    def is_running(self) -> bool:
        proc = self._proc
        return bool(proc is not None and proc.poll() is None)

    def start(self, stream_url: str) -> None:
        if not stream_url:
            return
        if self._proc is not None and self._proc.poll() is None and stream_url == self._active_url:
            return
        self.stop()
        self.chunk_dir.mkdir(parents=True, exist_ok=True)
        output_pattern = self.chunk_dir / "chunk_%Y%m%d_%H%M%S.mp3"
        cmd = [
            self.ffmpeg,
            "-hide_banner",
            "-loglevel",
            "warning",
            "-nostdin",
            "-y",
            "-rw_timeout",
            "10000000",
            "-i",
            stream_url,
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "64k",
            "-f",
            "segment",
            "-segment_time",
            str(self.chunk_seconds),
            "-reset_timestamps",
            "1",
            "-strftime",
            "1",
            str(output_pattern),
        ]
        self._proc = subprocess.Popen(  # noqa: S603
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._active_url = stream_url

    def stop(self, grace_sec: float = 2.0) -> None:
        proc = self._proc
        self._proc = None
        self._active_url = ""
        if proc is None:
            return
        if proc.poll() is not None:
            return
        try:
            proc.send_signal(signal.SIGINT)
            proc.wait(timeout=max(0.5, grace_sec))
        except Exception:
            proc.kill()
            proc.wait(timeout=1.0)
