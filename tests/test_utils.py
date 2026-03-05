from __future__ import annotations

import unittest

from src.common.utils import parse_track_flag, summarize_stream_url


class UtilsTests(unittest.TestCase):
    def test_parse_track_flag(self) -> None:
        self.assertTrue(parse_track_flag("1"))
        self.assertTrue(parse_track_flag("true"))
        self.assertFalse(parse_track_flag("0"))
        self.assertFalse(parse_track_flag("false"))
        self.assertIsNone(parse_track_flag("maybe"))

    def test_summarize_stream_url_with_auth_key(self) -> None:
        summary = summarize_stream_url(
            "https://a.zju.edu.cn/live/xx.m3u8?auth_key=1710000000-0-0-abc&foo=bar"
        )
        self.assertTrue(summary["present"])
        self.assertEqual(summary["host"], "a.zju.edu.cn")
        self.assertTrue(summary["has_auth_key"])
        self.assertIn("auth_key", summary["query_keys"])
        self.assertIn("foo", summary["query_keys"])
        self.assertTrue(summary["auth_key_expire_at_utc"])


if __name__ == "__main__":
    unittest.main()
