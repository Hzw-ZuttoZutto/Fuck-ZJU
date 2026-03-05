from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from src.live.models import StreamInfo


@dataclass
class ProviderFetchResult:
    provider: str
    success: bool
    result_err: Optional[int]
    result_err_msg: str
    stream_infos: list[StreamInfo]
    raw_streams: list[dict]
    error: str = ""
    diagnostics: dict[str, object] = field(default_factory=dict)

    def has_hls_stream(self) -> bool:
        return any(info.stream_m3u8 for info in self.stream_infos)
