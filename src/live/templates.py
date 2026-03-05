from __future__ import annotations

import json

from src.common.utils import html_escape
from src.live_video import build_hls_config


def render_index_html(course_id: int, sub_id: int, poll_interval: float) -> str:
    return f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>直播观看控制台</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; background: #0f172a; color: #e2e8f0; }}
    .wrap {{ max-width: 980px; margin: 24px auto; padding: 24px; background: #111827; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,.35); }}
    h1 {{ margin: 0 0 8px; font-size: 24px; }}
    .meta {{ color: #94a3b8; margin-bottom: 16px; }}
    .row {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }}
    button {{ background: #2563eb; border: none; color: #fff; padding: 10px 14px; border-radius: 8px; cursor: pointer; font-size: 14px; }}
    button:hover {{ background: #1d4ed8; }}
    .status {{ background: #0b1220; border: 1px solid #1e293b; border-radius: 8px; padding: 12px; margin-top: 10px; white-space: pre-wrap; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <h1>直播观看控制台</h1>
    <div class=\"meta\">course_id={course_id} | sub_id={sub_id} | 后台拉流轮询={poll_interval:.1f}s</div>
    <div class=\"row\">
      <button onclick=\"openPlayer('teacher')\">打开教师直播窗口</button>
      <button onclick=\"openPlayer('ppt')\">打开PPT窗口</button>
      <button onclick=\"openBoth()\">同时打开两个窗口</button>
    </div>
    <div id=\"status\" class=\"status\">加载中...</div>
    <div id=\"metrics\" class=\"status\">metrics 加载中...</div>
  </div>
  <script>
    function openPlayer(role) {{
      const title = role === 'teacher' ? '教师直播' : 'PPT直播';
      const features = 'width=1280,height=760,left=80,top=80';
      window.open('/player?role=' + role, title, features);
    }}
    function openBoth() {{
      openPlayer('teacher');
      setTimeout(() => openPlayer('ppt'), 120);
    }}

    async function refreshStatus() {{
      try {{
        const [streamsResp, metricsResp] = await Promise.all([
          fetch('/api/streams', {{ cache: 'no-store' }}),
          fetch('/api/metrics', {{ cache: 'no-store' }}),
        ]);
        const streams = await streamsResp.json();
        const metrics = await metricsResp.json();
        document.getElementById('status').textContent = JSON.stringify(streams, null, 2);
        document.getElementById('metrics').textContent = JSON.stringify(metrics, null, 2);
      }} catch (err) {{
        document.getElementById('status').textContent = '状态获取失败: ' + err;
      }}
    }}

    refreshStatus();
    setInterval(refreshStatus, 4000);
  </script>
</body>
</html>
"""


def render_player_html(role: str, hls_max_buffer: int) -> str:
    safe_role = html_escape(role)
    title = "教师直播" if role == "teacher" else "PPT直播"
    hls_config_json = json.dumps(build_hls_config(hls_max_buffer), ensure_ascii=False)

    return f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{title}</title>
  <style>
    body {{ margin: 0; background: #000; color: #ddd; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
    .top {{ position: fixed; left: 0; right: 0; top: 0; z-index: 10; display: flex; gap: 12px; align-items: center; background: rgba(15, 23, 42, .82); padding: 8px 12px; }}
    .badge {{ background: #2563eb; padding: 2px 8px; border-radius: 999px; font-size: 12px; }}
    .muted {{ color: #93c5fd; font-size: 12px; }}
    .error {{ color: #fca5a5; font-size: 12px; }}
    .hint {{ color: #fcd34d; font-size: 12px; }}
    video {{ width: 100vw; height: 100vh; object-fit: contain; background: #000; }}
    .center-play {{ position: fixed; inset: 0; display: flex; align-items: center; justify-content: center; z-index: 11; pointer-events: none; }}
    .center-play button {{ pointer-events: auto; border: none; background: rgba(37, 99, 235, .95); color: #fff; font-size: 16px; padding: 14px 28px; border-radius: 999px; cursor: pointer; box-shadow: 0 8px 30px rgba(0, 0, 0, .35); }}
    .center-play button:hover {{ background: rgba(29, 78, 216, .98); }}
  </style>
</head>
<body>
  <div class=\"top\">
    <span class=\"badge\">{title}</span>
    <span id=\"stream-name\">等待流信息...</span>
    <span id=\"play-state\" class=\"muted\">等待手动播放</span>
    <span id=\"updated-at\" class=\"muted\"></span>
    <span id=\"err\" class=\"error\"></span>
    <span id=\"hint\" class=\"hint\"></span>
  </div>
  <div id=\"play-layer\" class=\"center-play\"><button id=\"play-btn\" type=\"button\">点击播放</button></div>
  <video id=\"video\" playsinline></video>

  <script src=\"/static/hls.min.js\"></script>
  <script>
    const role = '{safe_role}';
    const video = document.getElementById('video');
    const playLayer = document.getElementById('play-layer');
    const playBtn = document.getElementById('play-btn');
    const streamName = document.getElementById('stream-name');
    const playState = document.getElementById('play-state');
    const updatedAt = document.getElementById('updated-at');
    const errEl = document.getElementById('err');
    const hintEl = document.getElementById('hint');
    const localPlaylistUrl = '/proxy/m3u8?role=' + encodeURIComponent(role);
    const hlsConfig = {hls_config_json};

    let currentUrl = '';
    let hls = null;
    let sourceReady = false;
    let userStarted = false;
    let audioUnlocked = false;
    let audioExpected = true;

    video.muted = true;
    video.defaultMuted = true;
    video.volume = 1.0;

    function destroyHls() {{
      if (hls) {{
        hls.destroy();
        hls = null;
      }}
    }}

    async function playUrl(url) {{
      if (!url || url === currentUrl) return;
      currentUrl = url;
      sourceReady = false;
      errEl.textContent = '';
      destroyHls();

      if (video.canPlayType('application/vnd.apple.mpegurl')) {{
        video.src = url;
        video.addEventListener('loadedmetadata', () => {{
          sourceReady = true;
          if (userStarted) {{
            void ensurePlayback();
          }}
        }}, {{ once: true }});
      }} else if (window.Hls && Hls.isSupported()) {{
        hls = new Hls(hlsConfig);
        hls.attachMedia(video);
        hls.on(Hls.Events.MEDIA_ATTACHED, () => {{
          try {{ hls.loadSource(url); }} catch (_) {{}}
        }});
        hls.on(Hls.Events.MANIFEST_PARSED, () => {{
          sourceReady = true;
          if (userStarted) {{
            void ensurePlayback();
          }}
        }});
        hls.on(Hls.Events.ERROR, (_, data) => {{
          if (!data || !data.fatal) return;
          if (data.type === Hls.ErrorTypes.NETWORK_ERROR) {{
            errEl.textContent = '网络抖动，自动重连中';
            try {{ hls.startLoad(); }} catch (_) {{}}
            return;
          }}
          if (data.type === Hls.ErrorTypes.MEDIA_ERROR) {{
            errEl.textContent = '媒体错误，尝试恢复';
            try {{ hls.recoverMediaError(); }} catch (_) {{}}
            return;
          }}
          errEl.textContent = '播放错误: ' + data.type;
          destroyHls();
          currentUrl = '';
          setTimeout(() => playUrl(localPlaylistUrl), 1000);
        }});
      }} else {{
        errEl.textContent = '当前浏览器不支持HLS播放';
        return;
      }}
    }}

    async function refresh() {{
      try {{
        const r = await fetch('/api/stream?role=' + encodeURIComponent(role), {{ cache: 'no-store' }});
        const data = await r.json();

        updatedAt.textContent = 'updated: ' + (data.updated_at_utc || '-');
        if (data.error) {{
          errEl.textContent = '后台错误: ' + data.error;
        }} else if (!errEl.textContent.startsWith('播放错误')) {{
          errEl.textContent = '';
        }}

        if (!data.stream) {{
          streamName.textContent = '当前暂无可用流';
          hintEl.textContent = '';
          return;
        }}

        streamName.textContent = data.stream.stream_name || (role + ' stream');
        if (role === 'teacher' && data.stream.voice_track_on === false) {{
          audioExpected = false;
          hintEl.textContent = '当前教师流上游标记 voice_track=0，可能无声音';
        }} else {{
          audioExpected = true;
          hintEl.textContent = '';
        }}
        await playUrl(localPlaylistUrl);
      }} catch (e) {{
        errEl.textContent = '请求失败: ' + e;
      }}
    }}

    async function ensurePlayback() {{
      if (!userStarted) {{
        playState.textContent = '等待手动播放';
        return;
      }}
      if (!currentUrl) return;
      if (!sourceReady && video.readyState < 2) {{
        playState.textContent = '已点击播放，连接中...';
        return;
      }}

      if (!audioExpected) {{
        video.muted = true;
        try {{
          await video.play();
          playState.textContent = '实时播放';
          errEl.textContent = '';
          playLayer.style.display = 'none';
        }} catch (_) {{
          playState.textContent = '等待播放';
        }}
        return;
      }}

      if (!audioUnlocked) {{
        video.muted = false;
        try {{
          await video.play();
          audioUnlocked = true;
          playState.textContent = '实时播放（音视频）';
          errEl.textContent = '';
          playLayer.style.display = 'none';
          return;
        }} catch (_) {{
          video.muted = true;
          try {{
            await video.play();
            playState.textContent = '实时播放（静音，尝试恢复声音）';
            errEl.textContent = '音频恢复失败，正在自动重试恢复声音';
            playLayer.style.display = 'none';
            void tryUnlockAudio();
            return;
          }} catch (_) {{
            playState.textContent = '等待播放';
            errEl.textContent = '手动播放失败，请再次点击播放';
            playLayer.style.display = '';
          }}
          return;
        }}
      }}

      if (!video.paused) {{
        return;
      }}
      try {{
        await video.play();
        playState.textContent = video.muted ? '实时播放（静音）' : '实时播放（音视频）';
        playLayer.style.display = 'none';
      }} catch (_) {{
      }}
    }}

    async function tryUnlockAudio() {{
      if (!audioExpected || audioUnlocked || !currentUrl) return;
      if (!sourceReady && video.readyState < 2) return;
      video.muted = false;
      try {{
        await video.play();
        audioUnlocked = true;
        playState.textContent = '实时播放（音视频）';
        errEl.textContent = '';
      }} catch (_) {{
        video.muted = true;
      }}
    }}

    video.controls = false;
    video.addEventListener('canplay', () => {{
      sourceReady = true;
      if (userStarted) {{
        void ensurePlayback();
      }}
    }});
    video.addEventListener('playing', () => {{
      playState.textContent = video.muted ? '实时播放（静音）' : '实时播放（音视频）';
      if (!video.muted) {{
        errEl.textContent = '';
      }}
      if (userStarted) {{
        playLayer.style.display = 'none';
      }}
    }});
    video.addEventListener('pause', () => {{
      if (currentUrl && !document.hidden) {{
        setTimeout(() => {{ void ensurePlayback(); }}, 120);
      }}
    }});
    document.addEventListener('visibilitychange', () => {{
      if (!document.hidden) {{
        void ensurePlayback();
      }}
    }});
    playBtn.addEventListener('click', async () => {{
      userStarted = true;
      playLayer.style.display = 'none';
      if (!currentUrl) {{
        playState.textContent = '已点击播放，等待流就绪...';
        return;
      }}
      await ensurePlayback();
    }});

    refresh();
    setInterval(refresh, 5000);
    setInterval(() => {{
      if (userStarted) {{
        void ensurePlayback();
      }}
    }}, 3000);
    setInterval(() => {{
      if (userStarted) {{
        void tryUnlockAudio();
      }}
    }}, 1500);
  </script>
</body>
</html>
"""
