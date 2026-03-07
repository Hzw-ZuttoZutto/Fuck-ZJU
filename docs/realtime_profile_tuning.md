# Realtime Profile Tuning Guide

Last updated: 2026-03-07

## Scope

This note records:

- model request-format compatibility strategy for fast analysis models
- normalized latency metrics for fair cross-chunk comparison
- end-to-end benchmark results from local mic -> SSH tunnel -> remote insight
- recommended production presets and tuning workflow

Constraint used for this benchmark: analysis model tier must be `>= gpt-4.1`.

## Request-format Compatibility (Model-Specific Branch)

File: `src/live/insight/openai_client.py`

Implemented behavior:

- For `gpt-4.1*` models:
  - use `text.verbosity=medium`
  - do **not** send `reasoning` block by default
- For `gpt-5*` models:
  - use `text.verbosity=low`
  - send `reasoning.effort=minimal`
- Runtime fallback:
  - if provider returns `Unsupported value ... Supported values are ...`, auto-adjust known fields (`text.verbosity`, `reasoning.effort`) and retry the request once for that field

This prevents runtime 400 errors caused by per-model request-contract differences.

## Normalized Metrics (Per Chunk)

Added to `realtime_profile.jsonl` (file: `src/live/mic.py`):

- `chunk_seconds`
- `stt_ms_per_audio_sec`
- `analysis_ms_per_audio_sec`
- `remote_ms_per_audio_sec`
- `queue_wait_ms_per_audio_sec`
- `stt_rtf`
- `analysis_rtf`
- `remote_rtf`

Definitions:

- `analysis_ms_per_audio_sec = analysis_round_trip_ms / chunk_seconds`
- `analysis_rtf = analysis_round_trip_ms / (chunk_seconds * 1000)`
- `remote_rtf = remote_total_ms / (chunk_seconds * 1000)`

Interpretation:

- `rtf < 1.0`: processing is faster than realtime (healthy)
- `rtf ~= 1.0`: near realtime limit
- `rtf > 1.0`: pipeline cannot keep up; queue growth risk

## Benchmark Matrix

Environment:

- Local: Windows mic publisher (dshow device)
- Transport: `ssh -L 18765:127.0.0.1:18765`
- Remote: `mic-listen` on clusters
- Duration: ~85s per scenario, steady-state means `chunk_seq >= 3`, status `ok`

| Scenario | Model | Chunk | E2E Avg (ms) | E2E P95 (ms) | Remote RTF Avg | Analysis RTF Avg | Queue Wait Avg (ms) |
|---|---|---:|---:|---:|---:|---:|---:|
| gpt5mini_10_default | gpt-5-mini | 10s | 15269.7 | 16240.5 | 0.527 | 0.441 | 70.17 |
| gpt41_10_default | gpt-4.1 | 10s | 13274.3 | 13929.8 | 0.327 | 0.217 | 0.00 |
| gpt41_10_tuned | gpt-4.1 | 10s | 12793.0 | 13390.8 | 0.279 | 0.186 | 0.17 |
| gpt41_8_tuned | gpt-4.1 | 8s | 10786.8 | 10983.5 | 0.348 | 0.229 | 0.50 |
| gpt41_6_tuned | gpt-4.1 | 6s | 8451.3 | 9313.5 | 0.409 | 0.317 | 0.18 |

## Best Known Config (Latency First, Quality Floor >= gpt-4.1)

Best latency in this run: `gpt41_6_tuned`.

`mic-listen`:

```bash
python3 -m src.main mic-listen \
  --host 127.0.0.1 \
  --port 18765 \
  --mic-upload-token <TOKEN> \
  --session-dir <SESSION_DIR> \
  --rt-profile-enabled \
  --rt-model gpt-4.1 \
  --rt-chunk-seconds 6 \
  --rt-context-window-seconds 60 \
  --rt-context-min-ready 0 \
  --rt-context-recent-required 1 \
  --rt-context-wait-timeout-sec-1 0 \
  --rt-context-wait-timeout-sec-2 0 \
  --rt-stt-retry-count 2 \
  --rt-analysis-retry-count 2
```

`mic-publish`:

```bash
python -m src.main mic-publish \
  --target-url http://127.0.0.1:18765 \
  --mic-upload-token <TOKEN> \
  --device <DSHOW_DEVICE_OR_ALT_NAME> \
  --chunk-seconds 6 \
  --work-dir <UNIQUE_TEMP_DIR> \
  --ffmpeg-bin <FFMPEG_PATH>
```

## Practical Tuning Procedure

1. Start from `gpt-4.1`, chunk `10s`.
2. Enable profile and verify:
   - `final_status=ok` stable
   - `remote_rtf_p95 < 0.8`
3. Reduce chunk stepwise: `10 -> 8 -> 6`.
4. At each step, monitor:
   - `analysis_rtf_p95`
   - `remote_rtf_p95`
   - `queue_wait_ms` trend
5. Stop decreasing chunk when either:
   - `remote_rtf_p95` approaches `1.0`
   - queue wait grows continuously
6. Keep retries non-zero (`2` recommended) to avoid drops from transient provider failures.

## Notes

- Cross-machine send/receive timestamps can have clock skew. Treat absolute network delta carefully.
- Always use a unique `--work-dir` per run, otherwise stale chunks can cause fake backlog.
