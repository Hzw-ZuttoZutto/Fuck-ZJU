from __future__ import annotations

import json
import unittest
from unittest import mock

import requests

from src.live.providers.common import request_json


class _Resp:
    def __init__(self, *, payload: dict | None = None, text: str = "", status_code: int = 200) -> None:
        self._payload = payload
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"http {self.status_code}", response=mock.Mock(status_code=self.status_code))

    def json(self) -> dict:
        if self._payload is None:
            raise json.JSONDecodeError("not json", "", 0)
        return self._payload


class ProviderCommonTests(unittest.TestCase):
    def test_request_json_refreshes_and_retries_on_http_401(self) -> None:
        session = mock.Mock(spec=requests.Session)
        session.get.side_effect = [
            _Resp(payload={"msg": "未登录"}, status_code=401),
            _Resp(payload={"code": 0, "list": []}, status_code=200),
        ]

        token_state = {"value": "expired-token"}
        refresh_reasons: list[str] = []

        def _refresh(reason: str) -> tuple[bool, str]:
            refresh_reasons.append(reason)
            token_state["value"] = "fresh-token"
            return True, ""

        body, error = request_json(
            session=session,
            endpoint="https://example.test/live",
            params={"course_id": "1"},
            timeout=5,
            token="",
            token_provider=lambda: token_state["value"],
            refresh_auth_token=_refresh,
        )

        self.assertEqual(body, {"code": 0, "list": []})
        self.assertEqual(error, "")
        self.assertEqual(len(refresh_reasons), 1)
        self.assertEqual(session.get.call_count, 2)
        first_headers = session.get.call_args_list[0].kwargs["headers"]
        second_headers = session.get.call_args_list[1].kwargs["headers"]
        self.assertEqual(first_headers.get("Authorization"), "Bearer expired-token")
        self.assertEqual(second_headers.get("Authorization"), "Bearer fresh-token")

    def test_request_json_refreshes_on_json_auth_code(self) -> None:
        session = mock.Mock(spec=requests.Session)
        session.get.side_effect = [
            _Resp(payload={"code": 401, "msg": "login expired"}, status_code=200),
            _Resp(payload={"success": True, "result": {"err": 0, "data": []}}, status_code=200),
        ]

        refresh_called = {"count": 0}

        def _refresh(_reason: str) -> tuple[bool, str]:
            refresh_called["count"] += 1
            return True, ""

        body, error = request_json(
            session=session,
            endpoint="https://example.test/live",
            params={},
            timeout=5,
            token="tok",
            refresh_auth_token=_refresh,
        )

        self.assertTrue(body is not None)
        self.assertEqual(error, "")
        self.assertEqual(refresh_called["count"], 1)
        self.assertEqual(session.get.call_count, 2)

    def test_request_json_returns_auth_refresh_failed_when_refresh_fails(self) -> None:
        session = mock.Mock(spec=requests.Session)
        session.get.side_effect = [_Resp(payload={"msg": "token expired"}, status_code=401)]

        def _refresh(_reason: str) -> tuple[bool, str]:
            return False, "captcha required"

        body, error = request_json(
            session=session,
            endpoint="https://example.test/live",
            params={},
            timeout=5,
            token="tok",
            refresh_auth_token=_refresh,
        )

        self.assertIsNone(body)
        self.assertTrue(error.startswith("auth_refresh_failed:"))
        self.assertIn("captcha required", error)
        self.assertEqual(session.get.call_count, 1)


if __name__ == "__main__":
    unittest.main()
