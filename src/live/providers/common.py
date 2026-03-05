from __future__ import annotations

import json
from typing import Mapping

import requests

from src.common.constants import STREAM_TYPE_NAMES
from src.common.utils import parse_track_flag, summarize_stream_url, to_int_or_none
from src.live.models import StreamInfo


def auth_headers(token: str) -> dict[str, str]:
    headers = {"Accept-Language": "zh_cn"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def request_json(
    session: requests.Session,
    endpoint: str,
    params: Mapping[str, object],
    timeout: int,
    token: str,
) -> tuple[dict | None, str]:
    try:
        resp = session.get(
            endpoint,
            params=params,
            headers=auth_headers(token),
            timeout=timeout,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        return None, str(exc)

    try:
        return resp.json(), ""
    except json.JSONDecodeError:
        return None, resp.text[:300]


def to_stream_info(
    item: Mapping[str, object],
    *,
    fallback_sub_id: str,
    stream_m3u8: str | None = None,
    stream_play: str | None = None,
    type_name_override: str | None = None,
) -> StreamInfo:
    stream_type = to_int_or_none(item.get("type"))
    type_name = STREAM_TYPE_NAMES.get(
        stream_type,
        f"type_{stream_type}" if stream_type is not None else "unknown",
    )
    if type_name_override:
        type_name = type_name_override

    if stream_m3u8 is None:
        stream_m3u8 = str(item.get("stream_m3u8") or "")
    if stream_play is None:
        stream_play = str(item.get("stream_play") or "")

    return StreamInfo(
        type=stream_type,
        type_name=type_name,
        id=str(item.get("id") or ""),
        sub_id=str(item.get("sub_id") or fallback_sub_id),
        source_id=str(item.get("source_id") or ""),
        stream_id=str(item.get("stream_id") or ""),
        stream_name=str(item.get("stream_name") or ""),
        video_track=item.get("video_track"),
        video_track_on=parse_track_flag(item.get("video_track")),
        voice_track=item.get("voice_track"),
        voice_track_on=parse_track_flag(item.get("voice_track")),
        is_gortc=item.get("is_gortc"),
        stream_m3u8=stream_m3u8,
        stream_play=stream_play,
        stream_m3u8_meta=summarize_stream_url(stream_m3u8),
        stream_play_meta=summarize_stream_url(stream_play),
    )


def to_raw_stream(info: StreamInfo, source: str) -> dict:
    return {
        "source": source,
        "type": info.type,
        "type_name": info.type_name,
        "id": info.id,
        "sub_id": info.sub_id,
        "source_id": info.source_id,
        "stream_id": info.stream_id,
        "stream_name": info.stream_name,
        "video_track": info.video_track,
        "video_track_on": info.video_track_on,
        "voice_track": info.voice_track,
        "voice_track_on": info.voice_track_on,
        "is_gortc": info.is_gortc,
        "stream_m3u8": info.stream_m3u8,
        "stream_play": info.stream_play,
        "stream_m3u8_meta": info.stream_m3u8_meta,
        "stream_play_meta": info.stream_play_meta,
    }
