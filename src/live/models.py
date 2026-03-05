from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional

from src.common.utils import now_utc_iso


@dataclass
class StreamInfo:
    type: Optional[int]
    type_name: str
    id: str
    sub_id: str
    source_id: str
    stream_id: str
    stream_name: str
    video_track: object
    video_track_on: Optional[bool]
    voice_track: object
    voice_track_on: Optional[bool]
    is_gortc: object
    stream_m3u8: str
    stream_play: str
    stream_m3u8_meta: dict
    stream_play_meta: dict


@dataclass
class WatchSnapshot:
    updated_at_utc: str
    success: bool
    result_err: Optional[int]
    result_err_msg: str
    stream_count: int
    streams: dict[str, StreamInfo]
    raw_streams: list[dict]
    active_provider: str = ""
    provider_diagnostics: dict[str, dict] = field(default_factory=dict)
    error: str = ""

    def to_json_dict(self) -> dict:
        streams = {k: asdict(v) for k, v in self.streams.items()}
        return {
            "updated_at_utc": self.updated_at_utc,
            "success": self.success,
            "result_err": self.result_err,
            "result_err_msg": self.result_err_msg,
            "stream_count": self.stream_count,
            "streams": streams,
            "raw_streams": self.raw_streams,
            "active_provider": self.active_provider,
            "provider_diagnostics": self.provider_diagnostics,
            "error": self.error,
        }


@dataclass
class ProxyStats:
    playlist_requests: int = 0
    playlist_failures: int = 0
    playlist_stale_hits: int = 0
    playlist_retry_successes: int = 0
    consecutive_playlist_failures: int = 0

    asset_requests: int = 0
    asset_failures: int = 0
    asset_retry_successes: int = 0
    consecutive_asset_failures: int = 0

    updated_at_utc: str = field(default_factory=now_utc_iso)

    def to_json_dict(self) -> dict:
        body = asdict(self)
        body["updated_at_utc"] = now_utc_iso()
        return body
