from __future__ import annotations

import unittest
from unittest import mock

import requests

from src.live.joiner import JoinRoomClient


class _Resp:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return

    def json(self) -> dict:
        return self._payload


class JoinerTests(unittest.TestCase):
    def test_try_join_success(self) -> None:
        session = mock.Mock(spec=requests.Session)
        session.get.return_value = _Resp(
            {"success": True, "result": {"err": 0, "errMsg": "", "data": "stream-id-1"}}
        )
        session.post.return_value = _Resp(
            {"success": True, "result": {"err": 0, "errMsg": "", "data": "加入房间成功"}}
        )

        client = JoinRoomClient(
            session=session,
            token="tok",
            timeout=10,
            sub_id=2,
            user_id="u1",
            realname="u1",
        )
        result = client.try_join()
        self.assertTrue(result.attempted)
        self.assertTrue(result.success)
        self.assertEqual(result.stream_id, "stream-id-1")

    def test_try_join_without_stream_id(self) -> None:
        session = mock.Mock(spec=requests.Session)
        session.get.return_value = _Resp(
            {"success": True, "result": {"err": 0, "errMsg": "", "data": ""}}
        )

        client = JoinRoomClient(
            session=session,
            token="tok",
            timeout=10,
            sub_id=2,
            user_id="u1",
            realname="u1",
        )
        result = client.try_join()
        self.assertTrue(result.attempted)
        self.assertFalse(result.success)
        self.assertIn("stream_id", result.message)


if __name__ == "__main__":
    unittest.main()
