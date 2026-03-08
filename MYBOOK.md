# MYBOOK（精简流程版）：本地 PowerShell + `ssh wsl` 跑 Stream Mic（含钉钉）

目标：只保留必要流程，稳定跑通：
`mic-publish(stream) -> mic-listen(stream) -> 分析 -> DingTalk sent`



1. 本机路径（按你机器当前配置）：
- Python: `D:\All_The_App\anaconda3\envs\fuckclass\python.exe`
- ffmpeg: `D:\All_The_App\Anaconda3\envs\fuckclass\Library\bin\ffmpeg.exe`

## 1. 终端 A（先开）：远程 `mic-listen`

```bash
cd /home/hzw/repo_collection/Fuck-ZJU
source /home/hzw/APP/miniconda3/etc/profile.d/conda.sh
conda activate fuckclass
set -a; source .account; set +a

TOKEN="micstream001"
SESSION_DIR="mic_session_$(date +%Y%m%d_%H%M%S)"

python -m src.main mic-listen \
  --host 127.0.0.1 \
  --port 18765 \
  --session-dir "$SESSION_DIR" \
  --mic-upload-token "$TOKEN" \
  --rt-pipeline-mode stream \
  --rt-dingtalk-enabled \
  --rt-dingtalk-cooldown-sec 0 \
  --rt-asr-scene zh \
  --rt-asr-model fun-asr-realtime \
  --rt-hotwords-file config/realtime_hotwords.json \
  --rt-window-sentences 8 \
  --rt-stream-analysis-workers 32 \
  --rt-stream-queue-size 100 \
  --rt-asr-endpoint wss://dashscope.aliyuncs.com/api-ws/v1/inference \
  --rt-chunk-seconds 10 \
  --rt-model gpt-4.1-mini \
  --rt-keywords-file config/realtime_keywords.json \
  --rt-analysis-request-timeout-sec 15 \
  --rt-analysis-stage-timeout-sec 60 \
  --rt-analysis-retry-count 4 \
  --rt-analysis-retry-interval-sec 0.2 \
  --rt-context-recent-required 4 \
  --rt-context-wait-timeout-sec-1 1 \
  --rt-context-wait-timeout-sec-2 5
```

看到以下输出即正常：
- `session_dir=...`
- `dingtalk_trace_log=.../realtime_dingtalk_trace.jsonl`

## 2. 终端 B：本地端口转发

```powershell
ssh -N -L 18765:127.0.0.1:18765 wsl
```

## 3. 终端 C：本地 `mic-publish(stream)`

先查设备名：

```powershell
$py='D:\All_The_App\anaconda3\envs\fuckclass\python.exe'
$ff='D:\All_The_App\Anaconda3\envs\fuckclass\Library\bin\ffmpeg.exe'

& $py -m src.main mic-list-devices --ffmpeg-bin $ff
```

启动发布（`$token` 必须与终端 A 的 `TOKEN` 一致）：

```powershell
$py='D:\All_The_App\anaconda3\envs\fuckclass\python.exe'
$ff='D:\All_The_App\Anaconda3\envs\fuckclass\Library\bin\ffmpeg.exe'
$token='micstream001'
$device='麦克风阵列 (适用于数字麦克风的英特尔® 智音技术)'

& $py -m src.main mic-publish --target-url http://127.0.0.1:18765 --mic-upload-token $token --device $device --rt-pipeline-mode stream --stream-frame-duration-ms 120 --request-timeout-sec 20 --retry-base-sec 1.0 --retry-max-sec 12.0 --ffmpeg-bin $ff
```

## 4. 通过标准（只看这两条）

在终端 A 日志中：
- 出现 `[rt-dingtalk] sent ...`
- 没有 `[rt-dingtalk] send failed ...`

## 5. 停止

按顺序 `Ctrl+C`：
1. 终端 C（publish）
2. 终端 B（端口转发）
3. 终端 A（listen）
