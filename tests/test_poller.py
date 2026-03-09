from __future__ import annotations

import json
import time
import unittest
from unittest import mock

import requests

from src.live.poller import StreamPoller


class _Resp:
    def __init__(
        self,
        payload: dict | None = None,
        text: str = "",
        *,
        status_code: int = 200,
    ) -> None:
        self._payload = payload
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(
                f"http {self.status_code}",
                response=mock.Mock(status_code=self.status_code),
            )
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

    def test_fetch_retries_once_after_auth_refresh(self) -> None:
        session = mock.Mock(spec=requests.Session)
        screen_ok = _Resp(
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
                    ],
                },
            }
        )
        rtc_ok = _Resp({"success": True, "result": {"streams": []}})

        token_state = {"value": "expired"}
        observed_auth_headers: list[str] = []
        refresh_called = {"count": 0}

        def _refresh(_reason: str) -> tuple[bool, str]:
            refresh_called["count"] += 1
            token_state["value"] = "fresh"
            return True, ""

        def _get_side_effect(_url: str, **kwargs):
            headers = kwargs.get("headers") or {}
            observed_auth_headers.append(str(headers.get("Authorization") or ""))
            if len(observed_auth_headers) == 1:
                return _Resp({"msg": "未登录"}, status_code=401)
            if len(observed_auth_headers) == 2:
                return screen_ok
            if len(observed_auth_headers) == 3:
                return rtc_ok
            raise AssertionError(f"unexpected request count={len(observed_auth_headers)}")

        session.get.side_effect = _get_side_effect

        poller = StreamPoller(
            session=session,
            token="expired",
            timeout=10,
            course_id=1,
            sub_id=2,
            poll_interval=10,
            token_provider=lambda: token_state["value"],
            token_refresher=_refresh,
        )
        snapshot = poller._fetch_once()
        self.assertTrue(snapshot.success)
        self.assertIn("teacher", snapshot.streams)
        self.assertEqual(refresh_called["count"], 1)
        self.assertGreaterEqual(len(observed_auth_headers), 3)
        self.assertEqual(observed_auth_headers[0], "Bearer expired")
        self.assertEqual(observed_auth_headers[1], "Bearer fresh")
        metrics = poller.get_metrics()
        self.assertEqual(int(metrics.get("token_refresh_total", 0)), 1)
        self.assertEqual(int(metrics.get("token_refresh_failures", 0)), 0)

    def test_fetch_marks_auth_refresh_failure_in_snapshot_error(self) -> None:
        session = mock.Mock(spec=requests.Session)
        session.get.side_effect = [
            _Resp({"msg": "token expired"}, status_code=401),
            _Resp({"msg": "token expired"}, status_code=401),
        ]

        def _refresh(_reason: str) -> tuple[bool, str]:
            return False, "captcha required"

        poller = StreamPoller(
            session=session,
            token="expired",
            timeout=10,
            course_id=1,
            sub_id=2,
            poll_interval=10,
            token_refresher=_refresh,
        )
        snapshot = poller._fetch_once()
        self.assertFalse(snapshot.success)
        self.assertTrue(snapshot.error.startswith("auth_refresh_failed:"))
        metrics = poller.get_metrics()
        self.assertGreaterEqual(int(metrics.get("token_refresh_total", 0)), 1)
        self.assertGreaterEqual(int(metrics.get("token_refresh_failures", 0)), 1)

    def test_start_is_idempotent_and_restartable(self) -> None:
        session = mock.Mock(spec=requests.Session)
        poller = StreamPoller(
            session=session,
            token="tok",
            timeout=10,
            course_id=1,
            sub_id=2,
            poll_interval=10,
        )
        poller.poll_interval = 0.01
        snapshot = poller.get_snapshot()
        with mock.patch.object(poller, "_fetch_once", return_value=snapshot):
            poller.start()
            time.sleep(0.03)
            self.assertTrue(poller.is_running())
            first_thread = poller._thread

            poller.start()
            self.assertIs(poller._thread, first_thread)

            poller.stop()
            self.assertFalse(poller.is_running())

            poller.start()
            time.sleep(0.03)
            self.assertTrue(poller.is_running())
            self.assertIsNot(poller._thread, first_thread)
            poller.stop()
        self.assertFalse(poller.is_running())

    def test_run_catches_loop_exception_and_keeps_thread_alive(self) -> None:
        session = mock.Mock(spec=requests.Session)
        poller = StreamPoller(
            session=session,
            token="tok",
            timeout=10,
            course_id=1,
            sub_id=2,
            poll_interval=10,
        )
        poller.poll_interval = 0.01
        with mock.patch.object(poller, "_fetch_once", side_effect=RuntimeError("boom")):
            poller.start()
            try:
                time.sleep(0.05)
                self.assertTrue(poller.is_running())
                snapshot = poller.get_snapshot()
                self.assertFalse(snapshot.success)
                self.assertEqual(snapshot.result_err_msg, "poller_loop_exception")
                self.assertIn("poller loop exception", snapshot.error)
            finally:
                poller.stop()
        self.assertFalse(poller.is_running())


if __name__ == "__main__":
    unittest.main()
