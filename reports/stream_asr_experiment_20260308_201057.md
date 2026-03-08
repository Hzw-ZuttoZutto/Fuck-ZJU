# Stream ASR Connectivity & Latency Report

- Generated at: 2026-03-08T20:10:57.641259+08:00
- WAV source: https://dashscope.oss-cn-beijing.aliyuncs.com/samples/audio/paraformer/hello_world_female2.wav
- WAV info: {"channels": 1, "sample_width": 2, "sample_rate": 16000, "total_frames": 61353, "frame_bytes": 3200, "frame_ms": 100}
- Stage2 repeats per combination: 5
- Stage1 fatal stop triggered: False

## Stage1: Connectivity

- [PASS] scene=zh model=fun-asr-realtime events=6 finals=1 error=-
- [PASS] scene=zh model=fun-asr-realtime-2026-02-28 events=6 finals=1 error=-
- [PASS] scene=zh model=paraformer-realtime-v2 events=7 finals=1 error=-
- [PASS] scene=multi model=gummy-realtime-v1 events=7 finals=7 error=-
- [PASS] scene=multi model=paraformer-realtime-v2 events=7 finals=1 error=-

## Stage2: Average Latency

- [OK] scene=zh model=fun-asr-realtime samples=5/5 avg_ms=10189.25 min_ms=10138.314 max_ms=10282.934
- [OK] scene=zh model=fun-asr-realtime-2026-02-28 samples=5/5 avg_ms=10182.436 min_ms=10168.699 max_ms=10196.252
- [OK] scene=zh model=paraformer-realtime-v2 samples=5/5 avg_ms=10249.403 min_ms=10209.150 max_ms=10282.050
- [OK] scene=multi model=gummy-realtime-v1 samples=5/5 avg_ms=1357.609 min_ms=1309.424 max_ms=1422.625
- [OK] scene=multi model=paraformer-realtime-v2 samples=5/5 avg_ms=10312.02 min_ms=10241.613 max_ms=10386.734

## Stage3

- Deferred by decision: microphone end-to-before-DingTalk latency is not executed in this round.

## Raw JSON

```json
[
  {
    "stage": "stage1_connectivity",
    "scene": "zh",
    "model": "fun-asr-realtime",
    "run_index": 1,
    "success": true,
    "latency_ms": 10161.415,
    "final_text": "Hello world，这里是阿里巴巴语音实验室。",
    "final_event_type": "final",
    "error": "",
    "auth_or_quota_error": false,
    "event_count": 6,
    "final_count": 1
  },
  {
    "stage": "stage1_connectivity",
    "scene": "zh",
    "model": "fun-asr-realtime-2026-02-28",
    "run_index": 1,
    "success": true,
    "latency_ms": 10261.03,
    "final_text": "Hello world，这里是阿里巴巴语音实验室。",
    "final_event_type": "final",
    "error": "",
    "auth_or_quota_error": false,
    "event_count": 6,
    "final_count": 1
  },
  {
    "stage": "stage1_connectivity",
    "scene": "zh",
    "model": "paraformer-realtime-v2",
    "run_index": 1,
    "success": true,
    "latency_ms": 10222.453,
    "final_text": "Hello word, 这里是阿里巴巴语音实验室。",
    "final_event_type": "final",
    "error": "",
    "auth_or_quota_error": false,
    "event_count": 7,
    "final_count": 1
  },
  {
    "stage": "stage1_connectivity",
    "scene": "multi",
    "model": "gummy-realtime-v1",
    "run_index": 1,
    "success": true,
    "latency_ms": 1318.01,
    "final_text": "Hello",
    "final_event_type": "final",
    "error": "",
    "auth_or_quota_error": false,
    "event_count": 7,
    "final_count": 7
  },
  {
    "stage": "stage1_connectivity",
    "scene": "multi",
    "model": "paraformer-realtime-v2",
    "run_index": 1,
    "success": true,
    "latency_ms": 10186.896,
    "final_text": "Hello word, 这里是阿里巴巴语音实验室。",
    "final_event_type": "final",
    "error": "",
    "auth_or_quota_error": false,
    "event_count": 7,
    "final_count": 1
  },
  {
    "stage": "stage2_latency",
    "scene": "zh",
    "model": "fun-asr-realtime",
    "run_index": 1,
    "success": true,
    "latency_ms": 10138.314,
    "final_text": "Hello world，这里是阿里巴巴语音实验室。",
    "final_event_type": "final",
    "error": "",
    "auth_or_quota_error": false,
    "event_count": 6,
    "final_count": 1
  },
  {
    "stage": "stage2_latency",
    "scene": "zh",
    "model": "fun-asr-realtime",
    "run_index": 2,
    "success": true,
    "latency_ms": 10207.457,
    "final_text": "Hello world，这里是阿里巴巴语音实验室。",
    "final_event_type": "final",
    "error": "",
    "auth_or_quota_error": false,
    "event_count": 6,
    "final_count": 1
  },
  {
    "stage": "stage2_latency",
    "scene": "zh",
    "model": "fun-asr-realtime",
    "run_index": 3,
    "success": true,
    "latency_ms": 10282.934,
    "final_text": "Hello world，这里是阿里巴巴语音实验室。",
    "final_event_type": "final",
    "error": "",
    "auth_or_quota_error": false,
    "event_count": 6,
    "final_count": 1
  },
  {
    "stage": "stage2_latency",
    "scene": "zh",
    "model": "fun-asr-realtime",
    "run_index": 4,
    "success": true,
    "latency_ms": 10149.478,
    "final_text": "Hello world，这里是阿里巴巴语音实验室。",
    "final_event_type": "final",
    "error": "",
    "auth_or_quota_error": false,
    "event_count": 6,
    "final_count": 1
  },
  {
    "stage": "stage2_latency",
    "scene": "zh",
    "model": "fun-asr-realtime",
    "run_index": 5,
    "success": true,
    "latency_ms": 10168.067,
    "final_text": "Hello world，这里是阿里巴巴语音实验室。",
    "final_event_type": "final",
    "error": "",
    "auth_or_quota_error": false,
    "event_count": 6,
    "final_count": 1
  },
  {
    "stage": "stage2_latency",
    "scene": "zh",
    "model": "fun-asr-realtime-2026-02-28",
    "run_index": 1,
    "success": true,
    "latency_ms": 10185.12,
    "final_text": "Hello world，这里是阿里巴巴语音实验室。",
    "final_event_type": "final",
    "error": "",
    "auth_or_quota_error": false,
    "event_count": 6,
    "final_count": 1
  },
  {
    "stage": "stage2_latency",
    "scene": "zh",
    "model": "fun-asr-realtime-2026-02-28",
    "run_index": 2,
    "success": true,
    "latency_ms": 10196.252,
    "final_text": "Hello world，这里是阿里巴巴语音实验室。",
    "final_event_type": "final",
    "error": "",
    "auth_or_quota_error": false,
    "event_count": 6,
    "final_count": 1
  },
  {
    "stage": "stage2_latency",
    "scene": "zh",
    "model": "fun-asr-realtime-2026-02-28",
    "run_index": 3,
    "success": true,
    "latency_ms": 10168.699,
    "final_text": "Hello world，这里是阿里巴巴语音实验室。",
    "final_event_type": "final",
    "error": "",
    "auth_or_quota_error": false,
    "event_count": 6,
    "final_count": 1
  },
  {
    "stage": "stage2_latency",
    "scene": "zh",
    "model": "fun-asr-realtime-2026-02-28",
    "run_index": 4,
    "success": true,
    "latency_ms": 10177.611,
    "final_text": "Hello world，这里是阿里巴巴语音实验室。",
    "final_event_type": "final",
    "error": "",
    "auth_or_quota_error": false,
    "event_count": 6,
    "final_count": 1
  },
  {
    "stage": "stage2_latency",
    "scene": "zh",
    "model": "fun-asr-realtime-2026-02-28",
    "run_index": 5,
    "success": true,
    "latency_ms": 10184.496,
    "final_text": "Hello world，这里是阿里巴巴语音实验室。",
    "final_event_type": "final",
    "error": "",
    "auth_or_quota_error": false,
    "event_count": 6,
    "final_count": 1
  },
  {
    "stage": "stage2_latency",
    "scene": "zh",
    "model": "paraformer-realtime-v2",
    "run_index": 1,
    "success": true,
    "latency_ms": 10209.15,
    "final_text": "Hello word, 这里是阿里巴巴语音实验室。",
    "final_event_type": "final",
    "error": "",
    "auth_or_quota_error": false,
    "event_count": 7,
    "final_count": 1
  },
  {
    "stage": "stage2_latency",
    "scene": "zh",
    "model": "paraformer-realtime-v2",
    "run_index": 2,
    "success": true,
    "latency_ms": 10282.05,
    "final_text": "Hello word, 这里是阿里巴巴语音实验室。",
    "final_event_type": "final",
    "error": "",
    "auth_or_quota_error": false,
    "event_count": 7,
    "final_count": 1
  },
  {
    "stage": "stage2_latency",
    "scene": "zh",
    "model": "paraformer-realtime-v2",
    "run_index": 3,
    "success": true,
    "latency_ms": 10258.032,
    "final_text": "Hello word, 这里是阿里巴巴语音实验室。",
    "final_event_type": "final",
    "error": "",
    "auth_or_quota_error": false,
    "event_count": 7,
    "final_count": 1
  },
  {
    "stage": "stage2_latency",
    "scene": "zh",
    "model": "paraformer-realtime-v2",
    "run_index": 4,
    "success": true,
    "latency_ms": 10271.31,
    "final_text": "Hello word, 这里是阿里巴巴语音实验室。",
    "final_event_type": "final",
    "error": "",
    "auth_or_quota_error": false,
    "event_count": 7,
    "final_count": 1
  },
  {
    "stage": "stage2_latency",
    "scene": "zh",
    "model": "paraformer-realtime-v2",
    "run_index": 5,
    "success": true,
    "latency_ms": 10226.471,
    "final_text": "Hello word, 这里是阿里巴巴语音实验室。",
    "final_event_type": "final",
    "error": "",
    "auth_or_quota_error": false,
    "event_count": 7,
    "final_count": 1
  },
  {
    "stage": "stage2_latency",
    "scene": "multi",
    "model": "gummy-realtime-v1",
    "run_index": 1,
    "success": true,
    "latency_ms": 1422.625,
    "final_text": "Hello,",
    "final_event_type": "final",
    "error": "",
    "auth_or_quota_error": false,
    "event_count": 7,
    "final_count": 7
  },
  {
    "stage": "stage2_latency",
    "scene": "multi",
    "model": "gummy-realtime-v1",
    "run_index": 2,
    "success": true,
    "latency_ms": 1309.424,
    "final_text": "Hello",
    "final_event_type": "final",
    "error": "",
    "auth_or_quota_error": false,
    "event_count": 7,
    "final_count": 7
  },
  {
    "stage": "stage2_latency",
    "scene": "multi",
    "model": "gummy-realtime-v1",
    "run_index": 3,
    "success": true,
    "latency_ms": 1327.674,
    "final_text": "Hello，",
    "final_event_type": "final",
    "error": "",
    "auth_or_quota_error": false,
    "event_count": 7,
    "final_count": 7
  },
  {
    "stage": "stage2_latency",
    "scene": "multi",
    "model": "gummy-realtime-v1",
    "run_index": 4,
    "success": true,
    "latency_ms": 1416.183,
    "final_text": "Hello",
    "final_event_type": "final",
    "error": "",
    "auth_or_quota_error": false,
    "event_count": 7,
    "final_count": 7
  },
  {
    "stage": "stage2_latency",
    "scene": "multi",
    "model": "gummy-realtime-v1",
    "run_index": 5,
    "success": true,
    "latency_ms": 1312.137,
    "final_text": "Hello",
    "final_event_type": "final",
    "error": "",
    "auth_or_quota_error": false,
    "event_count": 7,
    "final_count": 7
  },
  {
    "stage": "stage2_latency",
    "scene": "multi",
    "model": "paraformer-realtime-v2",
    "run_index": 1,
    "success": true,
    "latency_ms": 10241.613,
    "final_text": "Hello word, 这里是阿里巴巴语音实验室。",
    "final_event_type": "final",
    "error": "",
    "auth_or_quota_error": false,
    "event_count": 7,
    "final_count": 1
  },
  {
    "stage": "stage2_latency",
    "scene": "multi",
    "model": "paraformer-realtime-v2",
    "run_index": 2,
    "success": true,
    "latency_ms": 10348.601,
    "final_text": "Hello word, 这里是阿里巴巴语音实验室。",
    "final_event_type": "final",
    "error": "",
    "auth_or_quota_error": false,
    "event_count": 7,
    "final_count": 1
  },
  {
    "stage": "stage2_latency",
    "scene": "multi",
    "model": "paraformer-realtime-v2",
    "run_index": 3,
    "success": true,
    "latency_ms": 10335.323,
    "final_text": "Hello word, 这里是阿里巴巴语音实验室。",
    "final_event_type": "final",
    "error": "",
    "auth_or_quota_error": false,
    "event_count": 7,
    "final_count": 1
  },
  {
    "stage": "stage2_latency",
    "scene": "multi",
    "model": "paraformer-realtime-v2",
    "run_index": 4,
    "success": true,
    "latency_ms": 10386.734,
    "final_text": "Hello word, 这里是阿里巴巴语音实验室。",
    "final_event_type": "final",
    "error": "",
    "auth_or_quota_error": false,
    "event_count": 7,
    "final_count": 1
  },
  {
    "stage": "stage2_latency",
    "scene": "multi",
    "model": "paraformer-realtime-v2",
    "run_index": 5,
    "success": true,
    "latency_ms": 10247.827,
    "final_text": "Hello word, 这里是阿里巴巴语音实验室。",
    "final_event_type": "final",
    "error": "",
    "auth_or_quota_error": false,
    "event_count": 7,
    "final_count": 1
  }
]
```
