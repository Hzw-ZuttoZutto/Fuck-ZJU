from __future__ import annotations

from typing import Iterable, Optional

from src.live.models import StreamInfo


def _teacher_score(info: StreamInfo, index: int) -> tuple[int, int, int, int, int]:
    # Prefer streams that explicitly report audio/video availability.
    voice_rank = 0 if info.voice_track_on is True else (1 if info.voice_track_on is None else 2)
    video_rank = 0 if info.video_track_on is True else (1 if info.video_track_on is None else 2)

    # Keep teacher stream preferred, but allow class stream with better AV quality to win.
    role_rank = 0 if info.type_name == "teacher" else (1 if info.type_name == "class" else 2)
    url_rank = 0 if info.stream_m3u8 else 1
    return (voice_rank, video_rank, role_rank, url_rank, index)


def select_teacher_stream(streams: Iterable[StreamInfo]) -> Optional[StreamInfo]:
    best: Optional[StreamInfo] = None
    best_score: Optional[tuple[int, int, int, int, int]] = None

    for index, info in enumerate(streams):
        score = _teacher_score(info, index)
        if best is None or score < best_score:
            best = info
            best_score = score

    if best and best.stream_m3u8:
        return best
    return None


def build_hls_config(max_buffer_length: int) -> dict:
    return {
        "enableWorker": True,
        "lowLatencyMode": True,
        "liveSyncDurationCount": 3,
        "liveMaxLatencyDurationCount": 8,
        "maxBufferLength": max(6, int(max_buffer_length)),
        "fragLoadingMaxRetry": 3,
        "levelLoadingMaxRetry": 3,
    }
