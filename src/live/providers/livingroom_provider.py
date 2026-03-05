from __future__ import annotations

import json
import urllib.parse
from dataclasses import dataclass

import requests

from src.common.constants import API_BASE
from src.live.providers.base import ProviderFetchResult
from src.live.providers.common import request_json, to_raw_stream, to_stream_info


@dataclass
class LivingRoomStreamProvider:
    session: requests.Session
    token: str
    timeout: int
    course_id: int
    sub_id: int
    tenant_code: str

    def fetch(self) -> ProviderFetchResult:
        diagnostics: dict[str, object] = {"architecture": "livingroom"}
        streams = []
        raw_streams = []

        config_body, config_error = request_json(
            self.session,
            f"{API_BASE}/courseapi/v2/play-template/get-config",
            {
                "tenant": self.tenant_code,
                "tenant_id": self.tenant_code,
                "course_id": str(self.course_id),
                "sub_id": str(self.sub_id),
            },
            self.timeout,
            self.token,
        )
        if config_body and isinstance(config_body.get("data"), dict):
            data_obj = config_body["data"]
            if isinstance(data_obj.get("data"), dict):
                config_obj = data_obj["data"]
                diagnostics["template_id"] = str(config_obj.get("template_id") or "")
                diagnostics["template_name"] = str(config_obj.get("name") or "")
                diagnostics["task_id"] = str(config_obj.get("id") or "")
                modules = config_obj.get("modules")
                if isinstance(modules, list):
                    diagnostics["module_codes"] = [
                        str(mod.get("code") or "")
                        for mod in modules
                        if isinstance(mod, dict) and mod.get("code")
                    ]
        elif config_error:
            diagnostics["template_error"] = config_error

        infosimple_body, infosimple_error = request_json(
            self.session,
            f"{API_BASE}/userapi/v1/infosimple",
            {},
            self.timeout,
            self.token,
        )
        if infosimple_body and isinstance(infosimple_body.get("params"), dict):
            params = infosimple_body["params"]
            diagnostics["rtc_screen_type"] = str(params.get("rtcScreenType") or "")
            diagnostics["rtc_student_stream"] = params.get("rtcStudentStream")
        elif infosimple_error:
            diagnostics["infosimple_error"] = infosimple_error

        live_body, live_error = request_json(
            self.session,
            f"{API_BASE}/courseapi/v2/course-live/search-live-course-list",
            {
                "all": "1",
                "course_id": str(self.course_id),
                "sub_id": str(self.sub_id),
                "with_sub_data": "1",
                "with_room_data": "1",
                "show_all": "1",
                "show_delete": "2",
            },
            self.timeout,
            self.token,
        )

        if live_body is None:
            return ProviderFetchResult(
                provider="livingroom",
                success=False,
                result_err=None,
                result_err_msg="http_error",
                stream_infos=[],
                raw_streams=[],
                error=live_error,
                diagnostics=diagnostics,
            )

        code = live_body.get("code")
        list_obj = live_body.get("list")
        if code != 0 or not isinstance(list_obj, list) or not list_obj:
            diagnostics["live_list_code"] = code
            diagnostics["live_list_msg"] = str(live_body.get("msg") or "")
            return ProviderFetchResult(
                provider="livingroom",
                success=False,
                result_err=None,
                result_err_msg="empty_live_list",
                stream_infos=[],
                raw_streams=[],
                error="",
                diagnostics=diagnostics,
            )

        matched = None
        for item in list_obj:
            if not isinstance(item, dict):
                continue
            if str(item.get("sub_id") or "") == str(self.sub_id):
                matched = item
                break
        if matched is None:
            matched = list_obj[0]

        diagnostics["sub_status"] = str(matched.get("sub_status") or "")
        diagnostics["sub_type"] = str(matched.get("sub_type") or "")
        diagnostics["room_type"] = str(matched.get("room_type") or "")

        sub_content = matched.get("sub_content")
        parsed_sub_content: dict[str, object] = {}
        if isinstance(sub_content, dict):
            parsed_sub_content = sub_content
        elif isinstance(sub_content, str) and sub_content.strip():
            try:
                maybe_obj = json.loads(sub_content)
                if isinstance(maybe_obj, dict):
                    parsed_sub_content = maybe_obj
            except json.JSONDecodeError:
                diagnostics["sub_content_error"] = "invalid_json"

        if not parsed_sub_content:
            return ProviderFetchResult(
                provider="livingroom",
                success=False,
                result_err=None,
                result_err_msg="sub_content_missing",
                stream_infos=[],
                raw_streams=[],
                error="",
                diagnostics=diagnostics,
            )

        self._append_output_stream(
            parsed_sub_content.get("output"),
            role="teacher",
            streams=streams,
            raw_streams=raw_streams,
        )
        self._append_output_stream(
            parsed_sub_content.get("output_student"),
            role="ppt",
            streams=streams,
            raw_streams=raw_streams,
        )

        if not streams:
            return ProviderFetchResult(
                provider="livingroom",
                success=False,
                result_err=None,
                result_err_msg="output_stream_missing",
                stream_infos=[],
                raw_streams=[],
                error="",
                diagnostics=diagnostics,
            )

        diagnostics["stream_count"] = len(streams)
        return ProviderFetchResult(
            provider="livingroom",
            success=True,
            result_err=0,
            result_err_msg="",
            stream_infos=streams,
            raw_streams=raw_streams,
            error="",
            diagnostics=diagnostics,
        )

    def _append_output_stream(
        self,
        output_obj: object,
        *,
        role: str,
        streams: list,
        raw_streams: list,
    ) -> None:
        if not isinstance(output_obj, dict):
            return

        m3u8 = str(output_obj.get("m3u8") or output_obj.get("m3u8_lhd") or "")
        stream_play = str(output_obj.get("rtmp") or output_obj.get("flv") or "")
        if not m3u8:
            return

        stream_id = self._extract_stream_id(m3u8)
        stream_type = 3 if role == "teacher" else 2

        info = to_stream_info(
            {
                "type": stream_type,
                "id": f"livingroom_{role}",
                "sub_id": str(self.sub_id),
                "source_id": "",
                "stream_id": stream_id,
                "stream_name": f"livingroom_{role}",
                "video_track": "1",
                # teacher stream is typically mixed AV in this architecture.
                "voice_track": "1" if role == "teacher" else None,
                "is_gortc": "0",
            },
            fallback_sub_id=str(self.sub_id),
            stream_m3u8=m3u8,
            stream_play=stream_play,
            type_name_override=role,
        )
        streams.append(info)
        raw_streams.append(to_raw_stream(info, source=f"livingroom_{role}"))

    @staticmethod
    def _extract_stream_id(url: str) -> str:
        parsed = urllib.parse.urlparse(url)
        name = parsed.path.rsplit("/", 1)[-1]
        if name.endswith(".m3u8"):
            name = name[:-5]
        return name
