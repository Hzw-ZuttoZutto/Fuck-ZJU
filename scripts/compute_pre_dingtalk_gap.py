#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any


def _to_int_or_none(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return None
    if text.startswith("-"):
        sign = -1
        digits = text[1:]
    else:
        sign = 1
        digits = text
    if not digits.isdigit():
        return None
    try:
        return sign * int(digits)
    except ValueError:
        return None


def _percentile(sorted_values: list[float], p: float) -> float | None:
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    ratio = max(0.0, min(1.0, float(p)))
    rank = (len(sorted_values) - 1) * ratio
    low = int(math.floor(rank))
    high = int(math.ceil(rank))
    if low == high:
        return float(sorted_values[low])
    left = float(sorted_values[low])
    right = float(sorted_values[high])
    return left + (right - left) * (rank - low)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def build_gap_report(*, rows: list[dict[str, Any]], min_samples: int, session_dir: Path, trace_path: Path) -> dict[str, Any]:
    sent_rows = [row for row in rows if str(row.get("status", "")).strip().lower() == "sent"]

    gaps: list[float] = []
    invalid_count = 0
    for row in sent_rows:
        pre_send_rel_ms = _to_int_or_none(row.get("pre_send_rel_ms"))
        asr_end_ms = _to_int_or_none(row.get("asr_end_ms"))
        if (
            pre_send_rel_ms is None
            or asr_end_ms is None
            or int(pre_send_rel_ms) < 0
            or int(asr_end_ms) < 0
        ):
            invalid_count += 1
            continue
        gap_ms = int(pre_send_rel_ms) - int(asr_end_ms)
        if gap_ms < 0:
            invalid_count += 1
            continue
        gaps.append(float(gap_ms))

    gaps.sort()
    valid_count = len(gaps)
    avg_gap_ms = round(sum(gaps) / valid_count, 3) if valid_count > 0 else None
    p95_gap_ms = round(float(_percentile(gaps, 0.95)), 3) if valid_count > 0 else None

    return {
        "generated_at": datetime.now().astimezone().isoformat(),
        "session_dir": str(session_dir),
        "trace_path": str(trace_path),
        "min_samples": int(min_samples),
        "total_rows": len(rows),
        "sent_rows": len(sent_rows),
        "count": valid_count,
        "valid_samples": valid_count,
        "invalid_count": int(invalid_count),
        "avg_gap_ms": avg_gap_ms,
        "min_gap_ms": round(min(gaps), 3) if valid_count > 0 else None,
        "max_gap_ms": round(max(gaps), 3) if valid_count > 0 else None,
        "p95_gap_ms": p95_gap_ms,
        "sample_insufficient": bool(valid_count < int(min_samples)),
    }


def _build_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Pre-DingTalk Gap Report",
        "",
        f"- Generated at: {report.get('generated_at', '')}",
        f"- Session dir: {report.get('session_dir', '')}",
        f"- Trace file: {report.get('trace_path', '')}",
        "",
        "## Summary",
        "",
        f"- Min required samples: {report.get('min_samples', 0)}",
        f"- Total rows: {report.get('total_rows', 0)}",
        f"- Sent rows: {report.get('sent_rows', 0)}",
        f"- Count: {report.get('count', 0)}",
        f"- Valid samples: {report.get('valid_samples', 0)}",
        f"- Invalid samples: {report.get('invalid_count', 0)}",
        f"- Avg gap (ms): {report.get('avg_gap_ms')}",
        f"- Min gap (ms): {report.get('min_gap_ms')}",
        f"- Max gap (ms): {report.get('max_gap_ms')}",
        f"- P95 gap (ms): {report.get('p95_gap_ms')}",
        f"- Sample insufficient: {report.get('sample_insufficient')}",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compute avg(pre_send_rel_ms - asr_end_ms) from DingTalk trace logs")
    parser.add_argument("--session-dir", required=True, help="Session directory that contains realtime_dingtalk_trace.jsonl")
    parser.add_argument("--min-samples", type=int, default=30, help="Minimum valid sample count")
    parser.add_argument("--output-json", default="", help="Output JSON report path")
    parser.add_argument("--output-md", default="", help="Output Markdown report path")
    args = parser.parse_args(argv)

    session_dir = Path(args.session_dir).expanduser().resolve()
    trace_path = session_dir / "realtime_dingtalk_trace.jsonl"
    if not trace_path.exists():
        print(f"[gap] trace file not found: {trace_path}")
        return 2

    rows = _read_jsonl(trace_path)
    report = build_gap_report(
        rows=rows,
        min_samples=max(1, int(args.min_samples)),
        session_dir=session_dir,
        trace_path=trace_path,
    )

    ts = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    default_prefix = Path("reports") / f"pre_dingtalk_gap_{ts}"
    output_json = Path(args.output_json).expanduser().resolve() if args.output_json else default_prefix.with_suffix(".json").resolve()
    output_md = Path(args.output_md).expanduser().resolve() if args.output_md else default_prefix.with_suffix(".md").resolve()
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)

    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md.write_text(_build_markdown(report), encoding="utf-8")
    print(f"[gap] report_json={output_json}")
    print(f"[gap] report_md={output_md}")
    if bool(report.get("sample_insufficient", False)):
        print(
            "[gap] sample_insufficient=true "
            f"(valid_samples={report.get('valid_samples', 0)}, min_samples={report.get('min_samples', 0)})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
