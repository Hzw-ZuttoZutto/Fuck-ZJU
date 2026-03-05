# ZJU Classroom Live Tool

直播代理与课程扫描工具，统一入口为：

```bash
python -m src.main <subcommand> ...
```

## 目录

- `src/main.py`：CLI 总入口
- `src/scan/`：课程扫描逻辑
- `src/live/`：直播轮询、代理、Web 服务
- `src/live_video.py`：教师流选择策略（优先音轨可用）
- `src/live_ppt.py`：PPT 流选择策略
- `tests/`：单元与集成测试
- `RUNBOOK.md`：运行与排障手册

## 快速开始

```bash
# 安装依赖（realtime insight 需要 openai sdk）
pip install -r requirements.txt

# 凭据文件（推荐，避免在命令行暴露密码）
cat > .account <<'EOF'
USERNAME=你的统一认证账号
PASSWORD=你的统一认证密码
EOF

# 语法检查 + 测试
python -m py_compile $(find src tests -name '*.py')
python -m unittest discover -s tests -v

# 扫描课程
python -m src.main scan --teacher '王强' --title '测试标题' --center 83650 --radius 0 --workers 1 --retries 1 --verbose

# 扫描课程（仅保留“直播中”）
python -m src.main scan \
  --teacher '王强' \
  --title '测试标题' \
  --center 83650 \
  --radius 0 \
  --require-live \
  --live-check-timeout 30 \
  --live-check-interval 2

# 启动直播代理
python -m src.main watch --course-id 83650 --sub-id <sub_id> --poll-interval 3 --port 8765 --no-browser

# 启动直播代理 + 录制（默认每10分钟切片；0=整场单文件）
python -m src.main watch \
  --course-id 83650 \
  --sub-id <sub_id> \
  --record-dir ./records \
  --record-segment-minutes 10 \
  --record-startup-av-timeout 15 \
  --record-recovery-window-sec 10

# 启动直播代理 + 录制 + 实时关键信息提取（10s 音频增量）
OPENAI_API_KEY=你的key python -m src.main watch \
  --course-id 83650 \
  --sub-id <sub_id> \
  --record-dir ./records \
  --rt-insight-enabled \
  --rt-stt-model gpt-4o-mini-transcribe \
  --rt-model gpt-5-mini \
  --rt-chunk-seconds 10 \
  --rt-context-window-seconds 180 \
  --rt-max-concurrency 5 \
  --rt-stage-timeout-sec 60 \
  --rt-context-min-ready 15 \
  --rt-context-recent-required 4 \
  --rt-context-wait-timeout-sec 15 \
  --rt-keywords-file config/realtime_keywords.json
```

凭据规则：

- 默认从工作区根目录 `.account` 读取 `USERNAME` 和 `PASSWORD`。
- 仍可通过 `--username/--password` 显式传入；CLI 传参优先级更高。

录制产物：

- 每段 `mp4`：`课程名_老师名_开始时间_结束时间.mp4`
- 每段 `mp3`：`课程名_老师名_开始时间_结束时间.mp3`
- 每段缺失日志：`课程名_老师名_开始时间_结束时间.missing.json`
- 会话汇总：`recording_session_report.json`
- 实时转写日志：`realtime_transcripts.jsonl`
- 实时结构化日志：`realtime_insights.jsonl`
- 实时中文镜像日志：`realtime_insights.log`

实时提取说明：

- 必须设置 `OPENAI_API_KEY`。
- 关键词默认文件：`config/realtime_keywords.json`。
- 实时流程为两阶段：`10s音频 -> STT转写 -> 文本上下文分析`。
- 紧急度为二分类：重要=95%，非重要或失败降级=10%。

本地浏览器观看（本地执行）：

```bash
ssh clusters -L 8765:127.0.0.1:8765
```

然后打开：

- `http://127.0.0.1:8765/player?role=teacher`
- `http://127.0.0.1:8765/player?role=ppt`
