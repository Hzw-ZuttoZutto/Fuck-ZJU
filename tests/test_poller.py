from __future__ import annotations

import json
import unittest
from unittest import mock

import requests

from src.live.poller import StreamPoller


class _Resp:
    def __init__(self, payload: dict | None = None, text: str = "") -> None:
        self._payload = payload
        self.text = text

    def raise_for_status(self) -> None:
        return

    def json(self) -> dict:
        if self._payload is None:
            raise json.JSONDecodeError("x", "", 0)
        return self._payload


class PollerTests(unittest.TestCase):
    def test_fetch_success(self) -> None:
        session = mock.Mock(spec=requests.Session)
        session.get.side_effect = [
            _Resp(
                {
                    "success": True,
                    "result": {
                        "err": 0,
                        "errMsg": "",
                        "data": [
                            {
                                "type": 3,
                                "id": "1",
                                "sub_id": "2",
                                "source_id": "3",
                                "stream_id": "4",
                                "stream_name": "teacher-room",
                                "video_track": "1",
                                "voice_track": "1",
                                "stream_m3u8": "https://x.cmc.zju.edu.cn/t.m3u8",
                                "stream_play": "",
                            },
                            {
                                "type": 2,
                                "id": "5",
                                "sub_id": "2",
                                "source_id": "3",
                                "stream_id": "6",
                                "stream_name": "ppt-room",
                                "video_track": "1",
                                "voice_track": "0",
                                "stream_m3u8": "https://x.cmc.zju.edu.cn/p.m3u8",
                                "stream_play": "",
                            },
                        ],
                    },
                }
            ),
            _Resp(
                {
                    "success": True,
                    "result": {
                        "streams": [
                            {
                                "type": 4,
                                "id": "7",
                                "sub_id": "2",
                                "source_id": "9",
                                "stream_id": "8",
                                "stream_name": "class-room",
                                "video_track": "1",
                                "voice_track": "1",
                            }
                        ]
                    },
                }
            ),
        ]

        poller = StreamPoller(
            session=session,
            token="tok",
            timeout=10,
            course_id=1,
            sub_id=2,
            poll_interval=10,
        )
        snapshot = poller._fetch_once()
        self.assertTrue(snapshot.success)
        self.assertIn("teacher", snapshot.streams)
        self.assertIn("ppt", snapshot.streams)
        self.assertEqual(snapshot.stream_count, 3)
        self.assertIn("class", snapshot.streams)

    def test_fetch_fallback_to_livingroom_provider(self) -> None:
        session = mock.Mock(spec=requests.Session)
        session.get.side_effect = [
            _Resp(
                {
                    "success": True,
                    "result": {
                        "err": 0,
                        "errMsg": "",
                        "data": [],
                    },
                }
            ),
            _Resp({"success": True, "result": None}),
            _Resp(
                {
                    "success": True,
                    "data": {
                        "code": 200,
                        "msg": "success",
                        "data": {
                            "id": "1276762",
                            "template_id": "27217",
                            "name": "ai数字教师",
                        },
                    },
                }
            ),
            _Resp(
                {
                    "code": 200,
                    "message": "查询成功",
                    "params": {
                        "rtcScreenType": "merge",
                        "rtcStudentStream": 1,
                    },
                }
            ),
            _Resp(
                {
                    "code": 0,
                    "msg": "获取直播课列表成功",
                    "list": [
                        {
                            "sub_id": "2",
                            "sub_status": "1",
                            "sub_type": "course_live",
                            "room_type": "0",
                            "sub_content": json.dumps(
                                {
                                    "output": {
                                        "m3u8": "https://livepgc.cmc.zju.edu.cn/pgc/teacher.m3u8?auth_key=abc",
                                        "rtmp": "rtmp://livepgc.cmc.zju.edu.cn/pgc/teacher",
                                    },
                                    "output_student": {
                                        "m3u8": "https://livepgc.cmc.zju.edu.cn/pgc/ppt.m3u8?auth_key=xyz",
                                        "rtmp": "rtmp://livepgc.cmc.zju.edu.cn/pgc/ppt",
                                    },
                                },
                                ensure_ascii=False,
                            ),
                        }
                    ],
                }
            ),
        ]

        poller = StreamPoller(
            session=session,
            token="tok",
            timeout=10,
            course_id=1,
            sub_id=2,
            poll_interval=10,
            tenant_code="112",
        )
        snapshot = poller._fetch_once()
        self.assertTrue(snapshot.success)
        self.assertEqual(snapshot.active_provider, "livingroom")
        self.assertIn("teacher", snapshot.streams)
        self.assertIn("ppt", snapshot.streams)
        self.assertTrue(snapshot.streams["teacher"].stream_m3u8.endswith("auth_key=abc"))
        self.assertTrue(snapshot.streams["ppt"].stream_m3u8.endswith("auth_key=xyz"))
        self.assertIn("livingroom", snapshot.provider_diagnostics)

    def test_fetch_http_error(self) -> None:
        session = mock.Mock(spec=requests.Session)
        session.get.side_effect = requests.RequestException("boom")
        poller = StreamPoller(
            session=session,
            token="tok",
            timeout=10,
            course_id=1,
            sub_id=2,
            poll_interval=10,
        )
        snapshot = poller._fetch_once()
        self.assertFalse(snapshot.success)
        self.assertTrue(snapshot.error)

    def test_fetch_json_error(self) -> None:
        session = mock.Mock(spec=requests.Session)
        session.get.side_effect = [
            _Resp(None, text="not-json"),
            _Resp({"success": True, "result": {"streams": []}}),
        ]
        poller = StreamPoller(
            session=session,
            token="tok",
            timeout=10,
            course_id=1,
            sub_id=2,
            poll_interval=10,
        )
        snapshot = poller._fetch_once()
        self.assertFalse(snapshot.success)
        self.assertEqual(snapshot.result_err_msg, "http_error")
        self.assertEqual(snapshot.error, "not-json")


if __name__ == "__main__":
    unittest.main()
