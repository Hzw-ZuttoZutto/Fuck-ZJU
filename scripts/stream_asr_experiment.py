#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
import wave
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from src.common.account import resolve_dashscope_api_key
from src.live.insight.stream_asr import DashScopeRealtimeAsrClient, RealtimeAsrEvent

MODEL_MATRIX: list[tuple[str, str]] = [
    ("zh", "fun-asr-realtime"),
    ("zh", "fun-asr-realtime-2026-02-28"),
    ("zh", "paraformer-realtime-v2"),
    ("multi", "gummy-realtime-v1"),
    ("multi", "paraformer-realtime-v2"),
]

DEFAULT_WAV_URL = "https://dashscope.oss-cn-beijing.aliyuncs.com/samples/audio/paraformer/hello_world_female2.wav"
AUTH_OR_QUOTA_PATTERNS = [
    "invalid api key",
    "apikey",
    "access denied",
    "unauthorized",
    "authentication",
    "quota",
    "余额",
    "额度",
    "insufficient",
    "account",
    "401",
    "403",
]


@dataclass
class RunResult:
    stage: str
    scene: str
    model: str
    run_index: int
    success: bool
    latency_ms: float | None
    final_text: str
    final_event_type: str
    error: str
    auth_or_quota_error: bool
    event_count: int
    final_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "scene": self.scene,
            "model": self.model,
            "run_index": self.run_index,
            "success": self.success,
            "latency_ms": self.latency_ms,
            "final_text": self.final_text,
            "final_event_type": self.final_event_type,
            "error": self.error,
            "auth_or_quota_error": self.auth_or_quota_error,
            "event_count": self.event_count,
            "final_count": self.final_count,
        }


def _download_wav(url: str, dest: Path) -> None:
    req = Request(url, headers={"User-Agent": "stream-asr-experiment/1.0"})
    with urlopen(req, timeout=20) as resp:  # noqa: S310
        body = resp.read()
    dest.write_bytes(body)


def _load_wav_frames(path: Path, *, frame_ms: int) -> tuple[list[bytes], dict[str, int]]:
    with wave.open(str(path), "rb") as wf:
        channels = int(wf.getnchannels())
        sample_width = int(wf.getsampwidth())
        sample_rate = int(wf.getframerate())
        total_frames = int(wf.getnframes())
        raw = wf.readframes(total_frames)
    if sample_width != 2:
        raise ValueError(f"only PCM16 wav is supported, got sample_width={sample_width}")
    frame_bytes = max(320, int(sample_rate * channels * sample_width * frame_ms / 1000))
    out: list[bytes] = []
    for offset in range(0, len(raw), frame_bytes):
        block = raw[offset : offset + frame_bytes]
        if block:
            out.append(block)
    return out, {
        "channels": channels,
        "sample_width": sample_width,
        "sample_rate": sample_rate,
        "total_frames": total_frames,
        "frame_bytes": frame_bytes,
        "frame_ms": frame_ms,
    }


def _is_auth_or_quota_error(msg: str) -> bool:
    text = str(msg or "").strip().lower()
    if not text:
        return False
    return any(pattern in text for pattern in AUTH_OR_QUOTA_PATTERNS)


def _run_once(
    *,
    stage: str,
    scene: str,
    model: str,
    run_index: int,
    api_key: str,
    endpoint: str,
    hotwords: list[str],
    translation_targets: list[str],
    frames: list[bytes],
    frame_ms: int,
    wait_final_sec: float,
) -> RunResult:
    events: list[RealtimeAsrEvent] = []
    errors: list[str] = []
    first_send_ts: float | None = None
    first_final_ts: float | None = None
    first_final_event: RealtimeAsrEvent | None = None

    def on_event(event: RealtimeAsrEvent) -> None:
        nonlocal first_final_ts, first_final_event
        events.append(event)
        if event.is_final and first_final_event is None:
            first_final_event = event
            first_final_ts = time.monotonic()

    def on_error(message: str) -> None:
        errors.append(str(message or "").strip())

    client = DashScopeRealtimeAsrClient(
        scene=scene,
        model=model,
        api_key=api_key,
        endpoint=endpoint,
        hotwords=hotwords,
        translation_target_languages=translation_targets,
        on_event=on_event,
        on_error=on_error,
        log_fn=lambda _msg: None,
    )
    try:
        client.start()
        for payload in frames:
            if first_send_ts is None:
                first_send_ts = time.monotonic()
            ok = client.send_audio_frame(payload)
            if not ok:
                errors.append("send_audio_frame returned False")
                break
            time.sleep(max(0.0, frame_ms / 1000.0))

        deadline = time.monotonic() + max(0.5, float(wait_final_sec))
        while time.monotonic() < deadline:
            if first_final_event is not None:
                break
            if errors:
                break
            time.sleep(0.05)
    finally:
        client.stop()

    final_events = [item for item in events if item.is_final]
    first_error = errors[0] if errors else ""
    success = bool(events) and (first_final_event is not None or stage == "stage1_connectivity")
    latency_ms: float | None = None
    if first_send_ts is not None and first_final_ts is not None:
        latency_ms = round((first_final_ts - first_send_ts) * 1000.0, 3)
    if not success and not first_error:
        if not events:
            first_error = "no asr events received"
        elif first_final_event is None:
            first_error = "no final event received"
    return RunResult(
        stage=stage,
        scene=scene,
        model=model,
        run_index=run_index,
        success=success,
        latency_ms=latency_ms,
        final_text=(first_final_event.text if first_final_event else ""),
        final_event_type=(first_final_event.event_type if first_final_event else ""),
        error=first_error,
        auth_or_quota_error=_is_auth_or_quota_error(first_error),
        event_count=len(events),
        final_count=len(final_events),
    )


def _build_report_markdown(
    *,
    results: list[RunResult],
    wav_info: dict[str, int],
    wav_url: str,
    repeat_count: int,
    stage1_fatal_stop: bool,
    stage1_stop_reason: str,
) -> str:
    lines: list[str] = []
    lines.append("# Stream ASR Connectivity & Latency Report")
    lines.append("")
    lines.append(f"- Generated at: {datetime.now().astimezone().isoformat()}")
    lines.append(f"- WAV source: {wav_url}")
    lines.append(f"- WAV info: {json.dumps(wav_info, ensure_ascii=False)}")
    lines.append(f"- Stage2 repeats per combination: {repeat_count}")
    lines.append(f"- Stage1 fatal stop triggered: {stage1_fatal_stop}")
    if stage1_stop_reason:
        lines.append(f"- Stage1 stop reason: {stage1_stop_reason}")
    lines.append("")

    lines.append("## Stage1: Connectivity")
    lines.append("")
    stage1_rows = [item for item in results if item.stage == "stage1_connectivity"]
    if not stage1_rows:
        lines.append("- No stage1 rows.")
    else:
        for row in stage1_rows:
            status = "PASS" if row.success else "FAIL"
            lines.append(
                f"- [{status}] scene={row.scene} model={row.model} events={row.event_count} finals={row.final_count} "
                f"error={row.error or '-'}"
            )
    lines.append("")

    lines.append("## Stage2: Average Latency")
    lines.append("")
    stage2_rows = [item for item in results if item.stage == "stage2_latency"]
    if not stage2_rows:
        lines.append("- Deferred or skipped.")
    else:
        grouped: dict[tuple[str, str], list[RunResult]] = {}
        for row in stage2_rows:
            grouped.setdefault((row.scene, row.model), []).append(row)
        for scene, model in MODEL_MATRIX:
            group = grouped.get((scene, model), [])
            if not group:
                continue
            ok = [item for item in group if item.success and item.latency_ms is not None]
            if not ok:
                first_error = group[0].error if group else "unknown"
                lines.append(f"- [FAIL] scene={scene} model={model} no successful final latency, error={first_error}")
                continue
            latencies = [float(item.latency_ms or 0.0) for item in ok]
            avg = round(sum(latencies) / len(latencies), 3)
            lines.append(
                f"- [OK] scene={scene} model={model} samples={len(ok)}/{len(group)} "
                f"avg_ms={avg} min_ms={min(latencies):.3f} max_ms={max(latencies):.3f}"
            )
    lines.append("")

    lines.append("## Stage3")
    lines.append("")
    lines.append("- Deferred by decision: microphone end-to-before-DingTalk latency is not executed in this round.")
    lines.append("")

    lines.append("## Raw JSON")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps([item.to_dict() for item in results], ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run stream ASR connectivity + latency experiment")
    parser.add_argument(
        "--wav-url",
        default=DEFAULT_WAV_URL,
        help="Public wav URL used as sample input",
    )
    parser.add_argument(
        "--output-md",
        default="",
        help="Markdown report path; default: reports/stream_asr_experiment_<ts>.md",
    )
    parser.add_argument(
        "--output-json",
        default="",
        help="Raw JSON path; default: same prefix as markdown",
    )
    parser.add_argument("--repeat", type=int, default=5, help="Stage2 repeats per model combination")
    parser.add_argument("--frame-ms", type=int, default=100, help="Audio frame size in milliseconds")
    parser.add_argument("--wait-final-sec", type=float, default=6.0, help="Wait timeout for final result")
    parser.add_argument(
        "--asr-endpoint",
        default="wss://dashscope.aliyuncs.com/api-ws/v1/inference",
        help="DashScope websocket endpoint",
    )
    args = parser.parse_args()

    api_key, api_key_err = resolve_dashscope_api_key()
    if not api_key:
        print(f"[experiment] missing DashScope API key: {api_key_err}")
        return 2

    repeat = max(1, int(args.repeat))
    frame_ms = max(20, int(args.frame_ms))
    wait_final_sec = max(1.0, float(args.wait_final_sec))

    with tempfile.TemporaryDirectory() as td:
        wav_path = Path(td) / "sample.wav"
        _download_wav(str(args.wav_url), wav_path)
        frames, wav_info = _load_wav_frames(wav_path, frame_ms=frame_ms)

    if not frames:
        print("[experiment] wav sample has no readable pcm frames")
        return 3

    results: list[RunResult] = []
    stage1_fatal_stop = False
    stage1_stop_reason = ""

    print("[experiment] stage1 connectivity started")
    for scene, model in MODEL_MATRIX:
        targets = ["zh"] if scene == "multi" else ["zh"]
        row = _run_once(
            stage="stage1_connectivity",
            scene=scene,
            model=model,
            run_index=1,
            api_key=api_key,
            endpoint=str(args.asr_endpoint),
            hotwords=["签到", "作业", "测验", "重要通知"],
            translation_targets=targets,
            frames=frames,
            frame_ms=frame_ms,
            wait_final_sec=wait_final_sec,
        )
        results.append(row)
        print(
            f"[stage1] scene={scene} model={model} success={row.success} "
            f"events={row.event_count} finals={row.final_count} error={row.error or '-'}"
        )
        if (not row.success) and row.auth_or_quota_error:
            stage1_fatal_stop = True
            stage1_stop_reason = row.error
            print("[stage1] fatal auth/quota failure detected, skip remaining stages")
            break

    if not stage1_fatal_stop:
        print("[experiment] stage2 latency started")
        for scene, model in MODEL_MATRIX:
            for run_index in range(1, repeat + 1):
                targets = ["zh"] if scene == "multi" else ["zh"]
                row = _run_once(
                    stage="stage2_latency",
                    scene=scene,
                    model=model,
                    run_index=run_index,
                    api_key=api_key,
                    endpoint=str(args.asr_endpoint),
                    hotwords=["签到", "作业", "测验", "重要通知"],
                    translation_targets=targets,
                    frames=frames,
                    frame_ms=frame_ms,
                    wait_final_sec=wait_final_sec,
                )
                results.append(row)
                print(
                    f"[stage2] scene={scene} model={model} run={run_index} success={row.success} "
                    f"latency_ms={row.latency_ms} error={row.error or '-'}"
                )
                if (not row.success) and row.auth_or_quota_error:
                    stage1_fatal_stop = True
                    stage1_stop_reason = row.error
                    print("[stage2] fatal auth/quota failure detected, stop benchmark")
                    break
            if stage1_fatal_stop:
                break

    ts = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    default_prefix = Path("reports") / f"stream_asr_experiment_{ts}"
    output_md = Path(args.output_md).expanduser().resolve() if args.output_md else default_prefix.with_suffix(".md").resolve()
    output_json = (
        Path(args.output_json).expanduser().resolve()
        if args.output_json
        else default_prefix.with_suffix(".json").resolve()
    )
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.parent.mkdir(parents=True, exist_ok=True)

    report = _build_report_markdown(
        results=results,
        wav_info=wav_info,
        wav_url=str(args.wav_url),
        repeat_count=repeat,
        stage1_fatal_stop=stage1_fatal_stop,
        stage1_stop_reason=stage1_stop_reason,
    )
    output_md.write_text(report, encoding="utf-8")
    output_json.write_text(json.dumps([item.to_dict() for item in results], ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[experiment] report_md={output_md}")
    print(f"[experiment] report_json={output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
