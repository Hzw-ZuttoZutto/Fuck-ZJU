from __future__ import annotations

from typing import Iterable, Optional

from src.live.models import StreamInfo


def _ppt_score(info: StreamInfo, index: int) -> tuple[int, int, int, int]:
    if info.type_name == "ppt":
        role_rank = 0
    elif info.type_name == "blackboard":
        role_rank = 1
    elif info.type_name == "class":
        role_rank = 2
    else:
        role_rank = 3

    video_rank = 0 if info.video_track_on is True else (1 if info.video_track_on is None else 2)
    url_rank = 0 if info.stream_m3u8 else 1
    return (role_rank, video_rank, url_rank, index)


def select_ppt_stream(streams: Iterable[StreamInfo]) -> Optional[StreamInfo]:
    best: Optional[StreamInfo] = None
    best_score: Optional[tuple[int, int, int, int]] = None

    for index, info in enumerate(streams):
        score = _ppt_score(info, index)
        if best is None or score < best_score:
            best = info
            best_score = score

    if best and best.stream_m3u8:
        return best
    return None
