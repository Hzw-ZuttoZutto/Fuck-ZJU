set -e
cd /home/hzw/repo_collection/Fuck-ZJU
source /home/hzw/APP/miniconda3/etc/profile.d/conda.sh
conda activate fuckclass
if [ -f .account ]; then
  set -a
  source .account
  set +a
elif [ -f .acount ]; then
  set -a
  source .acount
  set +a
else
  echo ACCOUNT_FILE_MISSING
  exit 1
fi
SESSION_DIR=\"/home/hzw/repo_collection/Fuck-ZJU/mic_session_20260308_214638\"
OUT_LOG=\"/home/hzw/repo_collection/Fuck-ZJU/reports/e2e_mic_listen_20260308_214638.out.log\"
ERR_LOG=\"/home/hzw/repo_collection/Fuck-ZJU/reports/e2e_mic_listen_20260308_214638.err.log\"
TOKEN=\"e2e_676bdca2cf\"
nohup /home/hzw/APP/miniconda3/envs/fuckclass/bin/python -m src.main mic-listen \
  --host 127.0.0.1 \
  --port 18765 \
  --session-dir \"/home/hzw/repo_collection/Fuck-ZJU/mic_session_20260308_214638\" \
  --mic-upload-token \"e2e_676bdca2cf\" \
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
  --rt-context-wait-timeout-sec-2 5 \
  > \"/home/hzw/repo_collection/Fuck-ZJU/reports/e2e_mic_listen_20260308_214638.out.log\" 2> \"/home/hzw/repo_collection/Fuck-ZJU/reports/e2e_mic_listen_20260308_214638.err.log\" < /dev/null &
PID=$!
sleep 2
if ps -p 39284 > /dev/null; then STATE=running; else STATE=exited; fi
echo "SESSION_DIR=/home/hzw/repo_collection/Fuck-ZJU/mic_session_20260308_214638"
echo "TOKEN=e2e_676bdca2cf"
echo "LISTEN_PID=39284"
echo "LISTEN_OUT=/home/hzw/repo_collection/Fuck-ZJU/reports/e2e_mic_listen_20260308_214638.out.log"
echo "LISTEN_ERR=/home/hzw/repo_collection/Fuck-ZJU/reports/e2e_mic_listen_20260308_214638.err.log"
echo "LISTEN_STATE="
