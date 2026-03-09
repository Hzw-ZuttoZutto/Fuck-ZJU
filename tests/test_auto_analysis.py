from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.live.auto_analysis import (
    _analysis_args_to_tokens,
    _validate_analysis_args_map,
    load_auto_analysis_config,
)


def _write_config(base: Path, payload: dict) -> Path:
    path = base / "auto_config.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


class AutoAnalysisConfigTests(unittest.TestCase):
    def test_load_config_merges_duplicate_course_and_parses_slots(self) -> None:
        payload = {
            "timezone": "Asia/Shanghai",
            "scan": {"center": 82000, "radius": 10000},
            "runtime": {"main_tick_sec": 1},
            "analysis_args": {"poll_interval": 3, "rt_dingtalk_enabled": True, "rt_asr_model": "fun-asr-realtime"},
            "courses": [
                {
                    "title": "课程A",
                    "teacher": "老师A",
                    "slots": [{"start": "2026-03-09 22:12:00", "end": "2026-03-09 23:13:00"}],
                },
                {
                    "title": "课程A",
                    "teacher": "老师A",
                    "slots": [{"start": "2026-03-10 22:12:00", "end": "2026-03-10 23:13:00"}],
                },
            ],
        }
        with tempfile.TemporaryDirectory() as td:
            config_path = _write_config(Path(td), payload)
            cfg = load_auto_analysis_config(config_path)

        self.assertEqual(cfg.timezone, "Asia/Shanghai")
        self.assertEqual(len(cfg.courses), 1)
        self.assertEqual(cfg.courses[0].title, "课程A")
        self.assertEqual(cfg.courses[0].teacher, "老师A")
        self.assertEqual(len(cfg.courses[0].slots), 2)
        self.assertLess(cfg.courses[0].slots[0].start, cfg.courses[0].slots[1].start)

    def test_load_config_rejects_overlapped_slots(self) -> None:
        payload = {
            "timezone": "Asia/Shanghai",
            "analysis_args": {"rt_dingtalk_enabled": True, "rt_asr_model": "fun-asr-realtime"},
            "courses": [
                {
                    "title": "课程A",
                    "teacher": "老师A",
                    "slots": [
                        {"start": "2026-03-09 22:12:00", "end": "2026-03-09 23:13:00"},
                        {"start": "2026-03-09 22:50:00", "end": "2026-03-09 23:30:00"},
                    ],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as td:
            config_path = _write_config(Path(td), payload)
            with self.assertRaises(ValueError) as raised:
                load_auto_analysis_config(config_path)
        self.assertIn("overlapped slots", str(raised.exception))

    def test_load_config_rejects_non_shanghai_timezone(self) -> None:
        payload = {
            "timezone": "UTC",
            "analysis_args": {"rt_dingtalk_enabled": True, "rt_asr_model": "fun-asr-realtime"},
            "courses": [
                {
                    "title": "课程A",
                    "teacher": "老师A",
                    "slots": [{"start": "2026-03-09 22:12:00", "end": "2026-03-09 23:13:00"}],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as td:
            config_path = _write_config(Path(td), payload)
            with self.assertRaises(ValueError) as raised:
                load_auto_analysis_config(config_path)
        self.assertIn("timezone must be Asia/Shanghai", str(raised.exception))


class AutoAnalysisArgsTests(unittest.TestCase):
    def test_analysis_args_to_tokens(self) -> None:
        tokens = _analysis_args_to_tokens(
            {
                "poll_interval": 3,
                "rt_dingtalk_enabled": True,
                "rt_translation_target_languages": ["zh", "en"],
                "rt_api_base_url": "",
                "rt_asr_model": "fun-asr-realtime",
                "none_value": None,
                "disable_flag": False,
            }
        )
        self.assertIn("--poll-interval", tokens)
        self.assertIn("3", tokens)
        self.assertIn("--rt-dingtalk-enabled", tokens)
        self.assertIn("--rt-translation-target-languages", tokens)
        self.assertIn("zh,en", tokens)
        self.assertNotIn("--rt-api-base-url", tokens)
        self.assertNotIn("--disable-flag", tokens)
        self.assertNotIn("--none-value", tokens)

    def test_validate_analysis_args_map_rejects_forbidden_keys(self) -> None:
        err = _validate_analysis_args_map({"course_id": 1})
        self.assertIn("cannot include course_id", err)

    def test_validate_analysis_args_map_accepts_valid_shape(self) -> None:
        with mock.patch("src.live.auto_analysis._validate_analysis_args", return_value=""):
            err = _validate_analysis_args_map(
                {
                    "poll_interval": 3,
                    "rt_dingtalk_enabled": True,
                    "rt_asr_model": "fun-asr-realtime",
                    "rt_hotwords_file": "config/realtime_hotwords.json",
                }
            )
        self.assertEqual(err, "")


if __name__ == "__main__":
    unittest.main()
