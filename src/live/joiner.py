from __future__ import annotations

from dataclasses import dataclass

import requests

from src.common.constants import API_BASE
from src.common.utils import to_int_or_none


@dataclass
class JoinRoomResult:
    attempted: bool
    success: bool
    message: str
    stream_id: str = ""


class JoinRoomClient:
    def __init__(
        self,
        session: requests.Session,
        token: str,
        timeout: int,
        sub_id: int,
        user_id: str,
        realname: str,
    ) -> None:
        self.session = session
        self.token = token
        self.timeout = timeout
        self.sub_id = sub_id
        self.user_id = user_id
        self.realname = realname

    def try_join(self) -> JoinRoomResult:
        if not self.token:
            return JoinRoomResult(
                attempted=False,
                success=False,
                message="token is empty",
            )

        stream_id = self._fetch_stream_id()
        if not stream_id:
            return JoinRoomResult(
                attempted=True,
                success=False,
                message="failed to obtain local stream_id",
            )

        endpoint = f"{API_BASE}/courseapi/index.php/v2/meta/joinroom"
        payload = {
            "role": "student",
            "sub_id": self.sub_id,
            "user_id": self.user_id,
            "username": self.user_id,
            "realname": self.realname,
            "stream_id": stream_id,
            "stream_type": "camera",
            "room_type": "meta",
            "room_id": "",
            "video_track": "1",
            "voice_track": "1",
        }
        headers = {"Accept-Language": "zh_cn", "Authorization": f"Bearer {self.token}"}

        try:
            resp = self.session.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            body = resp.json()
        except (requests.RequestException, ValueError) as exc:
            return JoinRoomResult(
                attempted=True,
                success=False,
                message=f"joinroom http/json error: {exc}",
                stream_id=stream_id,
            )

        result_obj = body.get("result") if isinstance(body.get("result"), dict) else {}
        err = to_int_or_none(result_obj.get("err"))
        ok = bool(body.get("success")) and err in {None, 0}
        msg = str(result_obj.get("errMsg") or result_obj.get("data") or "")

        return JoinRoomResult(
            attempted=True,
            success=ok,
            message=msg or ("ok" if ok else "joinroom failed"),
            stream_id=stream_id,
        )

    def _fetch_stream_id(self) -> str:
        endpoint = f"{API_BASE}/courseapi/index.php/v2/meta/getstream"
        headers = {"Accept-Language": "zh_cn", "Authorization": f"Bearer {self.token}"}
        params = {"sub_id": self.sub_id, "user_id": self.user_id}

        try:
            resp = self.session.get(endpoint, params=params, headers=headers, timeout=self.timeout)
            resp.raise_for_status()
            body = resp.json()
        except (requests.RequestException, ValueError):
            return ""

        result_obj = body.get("result") if isinstance(body.get("result"), dict) else {}
        stream_id = result_obj.get("data")
        return str(stream_id or "")
