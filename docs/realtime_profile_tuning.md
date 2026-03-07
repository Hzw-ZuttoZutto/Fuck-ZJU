# 实时 Profile 分析报告

最后更新：2026-03-07

## 1. 范围

本报告汇总以下内容：

- 模型请求格式兼容性更新
- chunk 大小扫参结果（`5/8/10/15/20`）
- 7 个模型覆盖测试结果
- 两个相互独立的指标（不做加权合并）
- 调参建议

## 2. 兼容性更新

涉及文件：

- `src/live/insight/openai_client.py`
- `src/live/mic.py`
- `src/cli/parser.py`

已实现：

- 按模型分支构造请求：
  - `gpt-4.1*`：`text.verbosity=medium`，默认不带 `reasoning` 字段
  - `gpt-5*`：`text.verbosity=low`，`reasoning.effort=minimal`
- 不支持取值的回退机制：
  - 当服务端返回 `Unsupported value ... Supported values are ...` 时，自动调整已知字段（例如 `text.verbosity`）并重试
- 支持小数 chunk：
  - `mic-listen --rt-chunk-seconds` 支持 `float`
  - `mic-publish --chunk-seconds` 支持 `float`

## 3. 指标定义（分离评估）

重要说明：以下两个指标独立评估，绝不合并为单一加权分数。

### 3.1 指标 A：单位音频秒分析成本

- 使用字段：`analysis_ms_per_audio_sec`
- 定义：
  - `analysis_ms_per_audio_sec = analysis_round_trip_ms / chunk_seconds`
- 含义：
  - 越小越好
  - 表示每 1 秒音频对应的分析耗时成本

### 3.2 指标 B：最长分析等待时间

该指标直接对应你的核心关注点：
若关键事件刚好出现在 chunk 开头，从录音开始到分析结果可用需要等待多久。

- 单 chunk 派生指标：
  - `event_start_wait_ms = chunk_seconds * 1000 + remote_total_ms`
- 报告值：
  - `longest_wait_ms_max = max(event_start_wait_ms)`
- 含义：
  - 越小越好
  - 这是针对“chunk 开头事件”的纯最坏时延新鲜度指标

## 4. 实验设置

- 本地：Windows `mic-publish`（`dshow`）
- 远程：clusters 上的 `mic-listen`
- 传输：`ssh -L 18765:127.0.0.1:18765`
- 模型（7 个）：
  - `gpt-5-mini`
  - `gpt-5-nano`
  - `gpt-4.1-mini`
  - `gpt-4.1`
  - `gpt-4o-mini`
  - `gpt-4o`
  - `gpt-4.1-nano`
- chunk 大小：
  - `5/8/10/15/20` 秒
- 公共运行参数：
  - `--rt-context-window-seconds 60`
  - `--rt-context-min-ready 0`
  - `--rt-context-recent-required 1`
  - `--rt-context-wait-timeout-sec-1 0`
  - `--rt-context-wait-timeout-sec-2 0`
  - `--rt-stt-retry-count 2`
  - `--rt-analysis-retry-count 2`

## 5. 实验结果

### 5.1 指标 A：单位音频秒分析成本

数值格式：`avg (p95)`，单位 `ms/s`。

| Model | 5s | 8s | 10s | 15s | 20s |
|---|---:|---:|---:|---:|---:|
| gpt-4.1 | 353.2 (p95 456.9) | 286.1 (p95 350.5) | 176.7 (p95 223.5) | 111.2 (p95 128.2) | 86.9 (p95 100.0) |
| gpt-4.1-mini | 256.7 (p95 293.0) | 152.2 (p95 159.2) | 128.3 (p95 158.0) | 91.3 (p95 104.4) | 90.2 (p95 130.6) |
| gpt-4.1-nano | 190.7 (p95 201.9) | 124.0 (p95 130.6) | 98.9 (p95 102.5) | 63.7 (p95 67.9) | 46.9 (p95 48.4) |
| gpt-4o | 615.6 (p95 746.4) | 380.6 (p95 439.7) | 316.2 (p95 359.9) | 240.4 (p95 286.6) | 159.8 (p95 200.0) |
| gpt-4o-mini | 1034.0 (p95 1233.0) | 650.5 (p95 710.2) | 481.0 (p95 600.3) | 400.6 (p95 421.8) | 228.8 (p95 288.2) |
| gpt-5-mini | 881.0 (p95 1208.6) | 633.1 (p95 749.9) | 473.9 (p95 497.1) | 305.0 (p95 348.1) | 256.0 (p95 353.8) |
| gpt-5-nano | 577.5 (p95 637.7) | 402.4 (p95 462.9) | 307.0 (p95 367.0) | 192.6 (p95 240.5) | 160.7 (p95 199.8) |

各 chunk 最优模型（指标 A）：

- `5s`: `gpt-4.1-nano` (`190.7 ms/s`)
- `8s`: `gpt-4.1-nano` (`124.0 ms/s`)
- `10s`: `gpt-4.1-nano` (`98.9 ms/s`)
- `15s`: `gpt-4.1-nano` (`63.7 ms/s`)
- `20s`: `gpt-4.1-nano` (`46.9 ms/s`)

### 5.2 指标 B：最长分析等待时间

数值格式：`max (p95)`，单位 `ms`。

| Model | 5s | 8s | 10s | 15s | 20s |
|---|---:|---:|---:|---:|---:|
| gpt-4.1 | 8328 (p95 8237) | 12592 (p95 12355) | 14620 (p95 14347) | 18735 (p95 18731) | 23411 (p95 23410) |
| gpt-4.1-mini | 7533 (p95 7389) | 10806 (p95 10769) | 13449 (p95 13337) | 17900 (p95 17851) | 24058 (p95 23888) |
| gpt-4.1-nano | 7382 (p95 7206) | 10912 (p95 10852) | 13290 (p95 13277) | 17834 (p95 17726) | 22573 (p95 22540) |
| gpt-4o | 9742 (p95 9663) | 12948 (p95 12778) | 14639 (p95 14581) | 20378 (p95 20352) | 25635 (p95 25520) |
| gpt-4o-mini | 14469 (p95 14090) | 14478 (p95 14443) | 16716 (p95 16715) | 22398 (p95 22348) | 27522 (p95 27417) |
| gpt-5-mini | 13703 (p95 13664) | 14702 (p95 14685) | 15952 (p95 15914) | 21356 (p95 21242) | 28427 (p95 28066) |
| gpt-5-nano | 9957 (p95 9627) | 13602 (p95 13552) | 15138 (p95 15037) | 20197 (p95 20118) | 26530 (p95 26364) |

各 chunk 最优模型（指标 B）：

- `5s`: `gpt-4.1-nano` (`7382 ms`)
- `8s`: `gpt-4.1-mini` (`10806 ms`)
- `10s`: `gpt-4.1-nano` (`13290 ms`)
- `15s`: `gpt-4.1-nano` (`17834 ms`)
- `20s`: `gpt-4.1-nano` (`22573 ms`)

## 6. 调参建议

按目标选型，不做加权合并：

1. 若优先考虑计算效率（`analysis_ms_per_audio_sec`）：
   - 优先使用更大的 chunk（`15s` 或 `20s`）
   - 本轮优先模型：`gpt-4.1-nano`，其次 `gpt-4.1-mini`
2. 若优先考虑 chunk 开头关键事件的最坏新鲜度（`longest_wait_ms_max`）：
   - 先减小 chunk（`5s` 改善最明显）
   - 本轮优先模型：`gpt-4.1-nano` / `gpt-4.1-mini`
3. 若需要折中实用默认配置：
   - 从 `chunk=8s` + `gpt-4.1-mini` 开始
   - 若新鲜度仍慢，降到 `chunk=5s`
   - 若单位成本过高，升到 `chunk=10s`

## 7. 复现实验说明

- 每次运行保持唯一 `--work-dir`，避免旧 chunk 回放污染结果。
- 对比模型时，除模型外其余运行参数保持不变。
- 原始实验产物位于 `.tmp_e2e_profiles/`：
  - `*.profile.jsonl`
  - `*.insights.jsonl`
  - `*.transcripts.jsonl`
  - 汇总 CSV：`.tmp_e2e_profiles/chunk_model_report.csv`
