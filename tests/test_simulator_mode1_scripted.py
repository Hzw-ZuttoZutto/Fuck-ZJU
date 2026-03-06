from __future__ import annotations

import json
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

from src.cli.parser import build_parser
from src.live.insight.models import KeywordConfig, RealtimeInsightConfig
from src.live.insight.stage_processor import InsightStageProcessor
from src.simulator.cache_store import SimulationCacheStore
from src.simulator.mode_runner import run_mode
from src.simulator.models import (
    FeedConfig,
    Mode1Config,
    Mode1ScriptStep,
    Mode1SeqScript,
    Mode1ValidationConfig,
    Scenario,
    SimulatorMode,
)
from src.simulator.service import run_simulate


def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


class Mode1ScriptedTests(unittest.TestCase):
    def test_run_mode1_scripted_covers_retry_and_drop_statuses(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            chunk_paths: list[Path] = []
            for idx in range(1, 6):
                path = base / f"chunk_{idx:06d}.mp3"
                path.write_bytes(b"audio")
                chunk_paths.append(path)

            scenario = Scenario(
                mode=SimulatorMode.MODE1,
                name="m1-scripted",
                mode1=Mode1Config(
                    runner="scripted",
                    seq_strategy="source_seq",
                    validation=Mode1ValidationConfig(strict_fail=True),
                    scripts=[
                        Mode1SeqScript(
                            seq=1,
                            stt_script=[
                                Mode1ScriptStep(type="error", error="stt-fail-once"),
                                Mode1ScriptStep(type="ok", text="stt-ok"),
                            ],
                            analysis_script=[
                                Mode1ScriptStep(type="timeout_request", error="analysis-timeout-once"),
                                Mode1ScriptStep(
                                    type="ok",
                                    result={
                                        "summary": "analysis-ok",
                                        "context_summary": "scripted",
                                        "reason": "scripted",
                                    },
                                ),
                            ],
                        ),
                        Mode1SeqScript(
                            seq=2,
                            stt_script=[
                                Mode1ScriptStep(type="timeout_request", error="t1"),
                                Mode1ScriptStep(type="timeout_request", error="t2"),
                                Mode1ScriptStep(type="timeout_request", error="t3"),
                                Mode1ScriptStep(type="timeout_request", error="t4"),
                            ],
                        ),
                        Mode1SeqScript(
                            seq=3,
                            stt_script=[
                                Mode1ScriptStep(type="error", error="e1"),
                                Mode1ScriptStep(type="error", error="e2"),
                                Mode1ScriptStep(type="error", error="e3"),
                                Mode1ScriptStep(type="error", error="e4"),
                            ],
                        ),
                        Mode1SeqScript(
                            seq=4,
                            stt_script=[Mode1ScriptStep(type="ok", text="stt-ok")],
                            analysis_script=[
                                Mode1ScriptStep(type="timeout_request", error="a1"),
                                Mode1ScriptStep(type="timeout_request", error="a2"),
                                Mode1ScriptStep(type="timeout_request", error="a3"),
                                Mode1ScriptStep(type="timeout_request", error="a4"),
                            ],
                        ),
                        Mode1SeqScript(
                            seq=5,
                            stt_script=[Mode1ScriptStep(type="ok", text="stt-ok")],
                            analysis_script=[
                                Mode1ScriptStep(type="error", error="a1"),
                                Mode1ScriptStep(type="error", error="a2"),
                                Mode1ScriptStep(type="error", error="a3"),
                                Mode1ScriptStep(type="error", error="a4"),
                            ],
                        ),
                    ],
                ),
                feed=FeedConfig(mode="burst"),
            )
            processor = InsightStageProcessor(
                session_dir=base,
                config=RealtimeInsightConfig(
                    enabled=True,
                    stt_request_timeout_sec=8.0,
                    stt_stage_timeout_sec=32.0,
                    stt_retry_count=4,
                    stt_retry_interval_sec=0.2,
                    analysis_request_timeout_sec=15.0,
                    analysis_stage_timeout_sec=60.0,
                    analysis_retry_count=4,
                    analysis_retry_interval_sec=0.2,
                    context_recent_required=4,
                    context_target_chunks=18,
                    context_wait_timeout_sec_1=1.0,
                    context_wait_timeout_sec_2=5.0,
                    context_check_interval_sec=0.2,
                    use_dual_context_wait=True,
                    context_min_ready=0,
                ),
                keywords=KeywordConfig(),
                client=None,
                log_fn=lambda _: None,
            )

            result = run_mode(
                mode=SimulatorMode.MODE1,
                scenario=scenario,
                chunk_paths=chunk_paths,
                chunk_seconds=10,
                processor=processor,
                cache_store=SimulationCacheStore(base / "cache"),
                client=None,
                keywords=KeywordConfig(),
                stt_model="whisper-large-v3",
                analysis_model="gpt-5-mini",
                stt_request_timeout_sec=8.0,
                analysis_request_timeout_sec=15.0,
                precompute_workers=1,
                output_dir=base,
                log_fn=lambda _: None,
                seed_override=7,
            )

            self.assertEqual(result.summary["mode1_runner"], "scripted")
            self.assertEqual(result.summary["seq_strategy"], "source_seq")
            self.assertEqual(result.summary["emitted_seqs"], [1, 2, 3, 4, 5])

            transcript_rows = _read_jsonl(base / "realtime_transcripts.jsonl")
            insight_rows = _read_jsonl(base / "realtime_insights.jsonl")
            transcript_statuses = {row.get("status", "") for row in transcript_rows}
            insight_statuses = {row.get("status", "") for row in insight_rows}

            self.assertIn("ok", transcript_statuses)
            self.assertIn("transcript_drop_timeout", transcript_statuses)
            self.assertIn("transcript_drop_error", transcript_statuses)
            self.assertIn("ok", insight_statuses)
            self.assertIn("analysis_drop_timeout", insight_statuses)
            self.assertIn("analysis_drop_error", insight_statuses)
            self.assertTrue(any(int(row.get("attempt_count", 0)) > 1 for row in transcript_rows))
            self.assertTrue(any(int(row.get("attempt_count", 0)) > 1 for row in insight_rows))

    def test_run_simulate_mode1_scripted_strict_and_non_strict(self) -> None:
        parser = build_parser()
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            sim_root = base / "sim"
            run_dir = base / "runs"
            sim_root.mkdir(parents=True, exist_ok=True)
            run_dir.mkdir(parents=True, exist_ok=True)

            chunk_path = base / "chunk_000001.mp3"
            chunk_path.write_bytes(b"audio")

            scenario_strict = base / "m1_strict.yaml"
            scenario_strict.write_text(
                textwrap.dedent(
                    """
                    mode: 1
                    name: m1_strict
                    mode1:
                      runner: scripted
                      seq_strategy: source_seq
                      validation:
                        strict_fail: true
                        required_branches:
                          - analysis.drop_error
                    feed:
                      mode: burst
                    """
                ).strip(),
                encoding="utf-8",
            )

            args = parser.parse_args(
                [
                    "simulate",
                    "--mode",
                    "1",
                    "--scenario-file",
                    str(scenario_strict),
                    "--sim-root",
                    str(sim_root),
                    "--run-dir",
                    str(run_dir),
                ]
            )
            with (
                patch("src.simulator.service.collect_input_mp3_files", return_value=[chunk_path]),
                patch("src.simulator.service.preprocess_mp3_to_chunks", return_value=[chunk_path]),
                patch("src.simulator.service._build_openai_client", return_value=None),
            ):
                code = run_simulate(args)
            self.assertEqual(code, 1)

            scenario_non_strict = base / "m1_non_strict.yaml"
            scenario_non_strict.write_text(
                textwrap.dedent(
                    """
                    mode: 1
                    name: m1_non_strict
                    mode1:
                      runner: scripted
                      seq_strategy: source_seq
                      validation:
                        strict_fail: false
                        required_branches:
                          - analysis.drop_error
                    feed:
                      mode: burst
                    """
                ).strip(),
                encoding="utf-8",
            )
            args2 = parser.parse_args(
                [
                    "simulate",
                    "--mode",
                    "1",
                    "--scenario-file",
                    str(scenario_non_strict),
                    "--sim-root",
                    str(sim_root),
                    "--run-dir",
                    str(run_dir),
                ]
            )
            with (
                patch("src.simulator.service.collect_input_mp3_files", return_value=[chunk_path]),
                patch("src.simulator.service.preprocess_mp3_to_chunks", return_value=[chunk_path]),
                patch("src.simulator.service._build_openai_client", return_value=None),
            ):
                code2 = run_simulate(args2)
            self.assertEqual(code2, 0)


if __name__ == "__main__":
    unittest.main()
