from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


def _load_script_module(path: Path):
    spec = importlib.util.spec_from_file_location("compute_pre_dingtalk_gap", str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load script: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ComputePreDingTalkGapTests(unittest.TestCase):
    def test_build_gap_report_filters_invalid_and_negative_rows(self) -> None:
        root = Path(__file__).resolve().parents[1]
        script = _load_script_module(root / "scripts" / "compute_pre_dingtalk_gap.py")
        rows = [
            {"status": "sent", "pre_send_rel_ms": 300, "asr_end_ms": 100},
            {"status": "sent", "pre_send_rel_ms": 500, "asr_end_ms": 300},
            {"status": "sent", "pre_send_rel_ms": 200, "asr_end_ms": 250},
            {"status": "sent", "pre_send_rel_ms": None, "asr_end_ms": 100},
            {"status": "failed", "pre_send_rel_ms": 800, "asr_end_ms": 200},
        ]
        report = script.build_gap_report(
            rows=rows,
            min_samples=2,
            session_dir=Path("/tmp/session"),
            trace_path=Path("/tmp/session/realtime_dingtalk_trace.jsonl"),
        )
        self.assertEqual(report["sent_rows"], 4)
        self.assertEqual(report["valid_samples"], 2)
        self.assertEqual(report["invalid_count"], 2)
        self.assertEqual(report["avg_gap_ms"], 200.0)
        self.assertFalse(report["sample_insufficient"])

    def test_main_writes_json_and_markdown_reports(self) -> None:
        root = Path(__file__).resolve().parents[1]
        script = _load_script_module(root / "scripts" / "compute_pre_dingtalk_gap.py")
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            session_dir = base / "session_a"
            session_dir.mkdir(parents=True, exist_ok=True)
            trace_path = session_dir / "realtime_dingtalk_trace.jsonl"
            trace_rows = [
                {"status": "sent", "pre_send_rel_ms": 200, "asr_end_ms": 120},
                {"status": "sent", "pre_send_rel_ms": 260, "asr_end_ms": 130},
                {"status": "failed", "pre_send_rel_ms": 300, "asr_end_ms": 100},
            ]
            trace_path.write_text("\n".join(json.dumps(row) for row in trace_rows) + "\n", encoding="utf-8")

            out_json = base / "gap.json"
            out_md = base / "gap.md"
            rc = script.main(
                [
                    "--session-dir",
                    str(session_dir),
                    "--min-samples",
                    "2",
                    "--output-json",
                    str(out_json),
                    "--output-md",
                    str(out_md),
                ]
            )
            self.assertEqual(rc, 0)
            self.assertTrue(out_json.exists())
            self.assertTrue(out_md.exists())

            payload = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["valid_samples"], 2)
            self.assertEqual(payload["invalid_count"], 0)
            self.assertEqual(payload["avg_gap_ms"], 105.0)
            self.assertFalse(payload["sample_insufficient"])


if __name__ == "__main__":
    unittest.main()
