from __future__ import annotations

import unittest

from src.auth.cas_client import extract_bearer_token_from_cookie_value, extract_form_fields


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


if __name__ == "__main__":
    unittest.main()
