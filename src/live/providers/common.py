from __future__ import annotations

import json
from typing import Callable, Mapping

import requests

from src.common.constants import STREAM_TYPE_NAMES
from src.common.utils import parse_track_flag, summarize_stream_url, to_int_or_none
from src.live.models import StreamInfo

_AUTH_HTTP_STATUS = {401, 403}
_AUTH_MESSAGE_HINTS = (
    "未登录",
    "登录过期",
    "请先登录",
    "认证失败",
    "token失效",
    "token expired",
    "invalid token",
    "unauthorized",
    "not login",
)


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
    token: str = "",
    *,
    token_provider: Callable[[], str] | None = None,
    refresh_auth_token: Callable[[str], tuple[bool, str]] | None = None,
) -> tuple[dict | None, str]:
    resolved_token = _resolve_token(token=token, token_provider=token_provider)
    body, error, auth_failed = _request_json_once(
        session=session,
        endpoint=endpoint,
        params=params,
        timeout=timeout,
        token=resolved_token,
    )
    if not auth_failed or refresh_auth_token is None:
        return body, error

    refreshed, refresh_error = refresh_auth_token(error or "auth failure")
    if not refreshed:
        return None, f"auth_refresh_failed: {refresh_error or 'refresh callback returned failure'}"

    retry_token = _resolve_token(token=token, token_provider=token_provider)
    retry_body, retry_error, retry_auth_failed = _request_json_once(
        session=session,
        endpoint=endpoint,
        params=params,
        timeout=timeout,
        token=retry_token,
    )
    if retry_auth_failed:
        return None, f"auth_refresh_retry_failed: {retry_error or 'auth failure after refresh'}"
    return retry_body, retry_error


def _request_json_once(
    *,
    session: requests.Session,
    endpoint: str,
    params: Mapping[str, object],
    timeout: int,
    token: str,
) -> tuple[dict | None, str, bool]:
    try:
        resp = session.get(
            endpoint,
            params=params,
            headers=auth_headers(token),
            timeout=timeout,
        )
    except requests.RequestException as exc:
        status_code = _extract_status_code(exc)
        if status_code in _AUTH_HTTP_STATUS:
            return None, f"http_status_{status_code}", True
        return None, str(exc), False

    if resp.status_code in _AUTH_HTTP_STATUS:
        return None, f"http_status_{resp.status_code}", True

    try:
        resp.raise_for_status()
    except requests.RequestException as exc:
        status_code = _extract_status_code(exc)
        if status_code in _AUTH_HTTP_STATUS:
            return None, f"http_status_{status_code}", True
        return None, str(exc), False

    try:
        payload = resp.json()
    except json.JSONDecodeError:
        return None, resp.text[:300], False

    if not isinstance(payload, dict):
        return None, "response root is not JSON object", False

    auth_error = _extract_auth_error_from_payload(payload)
    if auth_error:
        return None, auth_error, True
    return payload, "", False


def _resolve_token(*, token: str, token_provider: Callable[[], str] | None) -> str:
    if token_provider is None:
        return str(token or "")
    try:
        return str(token_provider() or "")
    except Exception:
        return str(token or "")


def _extract_status_code(exc: requests.RequestException) -> int | None:
    response = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", None)
    if isinstance(status_code, int):
        return status_code
    return None


def _extract_auth_error_from_payload(payload: Mapping[str, object]) -> str:
    candidates: list[Mapping[str, object]] = [payload]
    result_obj = payload.get("result")
    if isinstance(result_obj, dict):
        candidates.append(result_obj)

    for item in candidates:
        for code in _extract_numeric_codes(item):
            if code in _AUTH_HTTP_STATUS:
                return f"json_auth_code_{code}"

        msg = _extract_text_message(item)
        if msg and _looks_like_auth_message(msg):
            return msg
    return ""


def _extract_numeric_codes(item: Mapping[str, object]) -> list[int]:
    out: list[int] = []
    for key in ("code", "err", "status", "error_code"):
        value = item.get(key)
        if value is None or isinstance(value, bool):
            continue
        try:
            out.append(int(value))
        except (TypeError, ValueError):
            continue
    return out


def _extract_text_message(item: Mapping[str, object]) -> str:
    for key in ("msg", "message", "errMsg", "error", "detail"):
        value = item.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _looks_like_auth_message(text: str) -> bool:
    lowered = text.strip().lower()
    if not lowered:
        return False
    for hint in _AUTH_MESSAGE_HINTS:
        if hint in lowered or hint in text:
            return True
    return False


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
