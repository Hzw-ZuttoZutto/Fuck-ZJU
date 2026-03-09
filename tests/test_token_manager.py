from __future__ import annotations

import unittest
from unittest import mock

import requests

from src.auth.token_manager import LoginTokenManager


class TokenManagerTests(unittest.TestCase):
    def test_refresh_success_updates_token(self) -> None:
        auth_client = mock.Mock()
        auth_client.login_and_get_token.return_value = "tok-new"

        manager = LoginTokenManager(
            auth_client=auth_client,
            username="u",
            password="p",
            center_course_id=1,
            authcode="",
            session_factory=lambda: requests.Session(),
        )

        ok, error = manager.refresh("initial_login", force=True)
        self.assertTrue(ok)
        self.assertEqual(error, "")
        self.assertEqual(manager.get_token(), "tok-new")
        snapshot = manager.snapshot()
        self.assertEqual(snapshot.token, "tok-new")
        self.assertTrue(snapshot.last_refresh_at_utc)
        self.assertEqual(snapshot.last_refresh_error, "")

    def test_refresh_failure_respects_cooldown(self) -> None:
        auth_client = mock.Mock()
        auth_client.login_and_get_token.side_effect = RuntimeError("login boom")

        manager = LoginTokenManager(
            auth_client=auth_client,
            username="u",
            password="p",
            center_course_id=1,
            authcode="",
            refresh_cooldown_sec=30.0,
            session_factory=lambda: requests.Session(),
        )

        ok1, err1 = manager.refresh("first", force=True)
        ok2, err2 = manager.refresh("second", force=False)

        self.assertFalse(ok1)
        self.assertIn("first", err1)
        self.assertIn("login boom", err1)
        self.assertFalse(ok2)
        self.assertIn("cooldown", err2)
        self.assertEqual(auth_client.login_and_get_token.call_count, 1)

    def test_force_refresh_bypasses_cooldown(self) -> None:
        auth_client = mock.Mock()
        auth_client.login_and_get_token.side_effect = [RuntimeError("login boom"), "tok-after-force"]

        manager = LoginTokenManager(
            auth_client=auth_client,
            username="u",
            password="p",
            center_course_id=1,
            authcode="",
            refresh_cooldown_sec=30.0,
            session_factory=lambda: requests.Session(),
        )

        ok1, _ = manager.refresh("first", force=True)
        ok2, err2 = manager.refresh("second", force=True)

        self.assertFalse(ok1)
        self.assertTrue(ok2)
        self.assertEqual(err2, "")
        self.assertEqual(manager.get_token(), "tok-after-force")
        self.assertEqual(auth_client.login_and_get_token.call_count, 2)


if __name__ == "__main__":
    unittest.main()
