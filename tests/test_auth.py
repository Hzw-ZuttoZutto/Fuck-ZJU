from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest import mock

from src.auth.cas_client import (
    ZJUAuthClient,
    extract_bearer_token_from_cookie_value,
    extract_form_fields,
)


class _Resp:
    def __init__(self, *, text: str = "", payload: dict | None = None, status_code: int = 200) -> None:
        self.text = text
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")

    def json(self) -> dict:
        if self._payload is None:
            raise ValueError("payload missing")
        return self._payload


class _FakeSession:
    def __init__(self, *, trust_env: bool = True) -> None:
        self.trust_env = trust_env
        self.cookies = [
            SimpleNamespace(
                name="_token",
                value='%7Bi%3A1%3Bs%3A6%3A%22_token%22%3Bi%3A2%3Bs%3A9%3A%22abc.def.gh%22%3B%7D',
            )
        ]
        self.trust_env_history: list[bool] = []

    def get(self, url: str, **_: object) -> _Resp:
        self.trust_env_history.append(self.trust_env)
        if "index.php?r=auth/login" in url:
            return _Resp(
                text=(
                    '<form id="fm1" action="/cas/login;jsessionid=abc">'
                    '<input name="execution" value="e1s1" />'
                    "</form>"
                )
            )
        if url.endswith("/v2/getKaptchaStatus"):
            return _Resp(text="false")
        if url.endswith("/v2/getPubKey"):
            return _Resp(payload={"modulus": "m", "exponent": "e"})
        if url.endswith("/js/login/security.js"):
            return _Resp(text="window.RSAUtils = {};")
        raise AssertionError(f"unexpected GET url: {url}")

    def post(self, url: str, **_: object) -> _Resp:
        self.trust_env_history.append(self.trust_env)
        if "/cas/login" not in url:
            raise AssertionError(f"unexpected POST url: {url}")
        return _Resp(text="ok")


class AuthTests(unittest.TestCase):
    def test_extract_form_fields(self) -> None:
        html = (
            '<form id="fm1" action="/cas/login;jsessionid=abc">'
            '<input name="execution" value="e1s1" />'
            "</form>"
        )
        action, execution = extract_form_fields(html)
        self.assertEqual(action, "/cas/login;jsessionid=abc")
        self.assertEqual(execution, "e1s1")

    def test_extract_bearer_token(self) -> None:
        cookie = '%7Bi%3A1%3Bs%3A6%3A%22_token%22%3Bi%3A2%3Bs%3A9%3A%22abc.def.gh%22%3B%7D'
        self.assertEqual(extract_bearer_token_from_cookie_value(cookie), "abc.def.gh")

    def test_login_disables_env_proxy_temporarily_by_default(self) -> None:
        session = _FakeSession(trust_env=True)
        client = ZJUAuthClient(timeout=5, tenant_code="112")
        with mock.patch("src.auth.cas_client.encrypt_password_with_node", return_value="enc_pwd"):
            token = client.login_and_get_token(
                session=session,
                username="u",
                password="p",
                center_course_id=1,
                authcode="",
            )
        self.assertEqual(token, "abc.def.gh")
        self.assertTrue(session.trust_env)
        self.assertTrue(session.trust_env_history)
        self.assertTrue(all(v is False for v in session.trust_env_history))

    def test_login_keeps_env_proxy_when_disabled_explicitly(self) -> None:
        session = _FakeSession(trust_env=True)
        client = ZJUAuthClient(timeout=5, tenant_code="112", disable_env_proxy_for_login=False)
        with mock.patch("src.auth.cas_client.encrypt_password_with_node", return_value="enc_pwd"):
            token = client.login_and_get_token(
                session=session,
                username="u",
                password="p",
                center_course_id=1,
                authcode="",
            )
        self.assertEqual(token, "abc.def.gh")
        self.assertTrue(session.trust_env)
        self.assertTrue(session.trust_env_history)
        self.assertTrue(all(v is True for v in session.trust_env_history))


if __name__ == "__main__":
    unittest.main()
