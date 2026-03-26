"""LAN HTTP + WebSocket server — runs alongside pywebview in a daemon thread."""
from __future__ import annotations

import json
import socket
import threading
from pathlib import Path

from flask import Flask, request, jsonify
from flask_sock import Sock

# ── Constants ────────────────────────────────────────────────────────────────
LAN_PORT = 8765
UI_DIR   = Path(__file__).parent / "ui"

# Greeting strings — defined in Python so we can use json.dumps for safe JS encoding
_GREETING = (
    "你好！我是 AI 助手\N{SMILING FACE WITH OPEN MOUTH AND SMILING EYES}\n"
    "\u2022 说\u300c启动灵巧手\u300d初始化设备\n"
    "\u2022 说\u300c比个耶\u300d控制手部动作\n"
    "\u2022 说\u300c关闭灵巧手\u300d断开设备"
)
_MISSING_TMPL = "\u26a0\ufe0f 检测到以下配置未填写：{names}\n请点击右上角\u300c设置\u300d完成配置后再使用。"


def _build_shim() -> str:
    """Build the JS shim string with all user-visible text safely JSON-encoded."""
    greeting_js   = json.dumps(_GREETING,    ensure_ascii=True)
    missing_prefix = json.dumps("\u26a0\ufe0f 检测到以下配置未填写：", ensure_ascii=True)
    missing_suffix = json.dumps("\n请点击右上角\u300c设置\u300d完成配置后再使用。", ensure_ascii=True)
    label_model   = json.dumps("模型", ensure_ascii=True)
    sep           = json.dumps("\u3001", ensure_ascii=True)

    return f"""\
<script>
(function () {{
  if (typeof window.pywebview !== 'undefined') return;

  var _call = function (method, args) {{
    return fetch('/api/' + method, {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify(args)
    }}).then(function (r) {{ return r.json(); }});
  }};

  window.pywebview = {{
    api: {{
      send_message:  function (text) {{ return _call('send_message',  {{ text: text }}); }},
      get_settings:  function ()     {{ return _call('get_settings',  {{}}); }},
      save_settings: function (cfg)  {{ return _call('save_settings', {{ cfg: cfg }}); }},
      check_config:  function ()     {{ return _call('check_config',  {{}}); }},
      clear_chat:    function ()     {{ return _call('clear_chat',    {{}}); }},
      hand_running:  function ()     {{ return _call('hand_running',  {{}}); }},
    }}
  }};

  var _ws;
  function _connectWs() {{
    _ws = new WebSocket('ws://' + location.host + '/ws');
    _ws.onmessage = function (e) {{ try {{ eval(e.data); }} catch (ex) {{ console.error(ex); }} }};
    _ws.onclose   = function ()  {{ setTimeout(_connectWs, 3000); }};
  }}
  _connectWs();

  setTimeout(function () {{
    window.pywebview.api.check_config().then(function (r) {{
      addBubble({greeting_js}, false);
      if (r && r.missing && r.missing.length > 0) {{
        var labels = {{ api_key: 'API Key', base_url: 'Base URL', model: {label_model} }};
        var names  = r.missing.map(function (k) {{ return labels[k] || k; }}).join({sep});
        addBubble({missing_prefix} + names + {missing_suffix}, false);
      }}
    }}).catch(function (e) {{ console.error('check_config failed:', e); }});
  }}, 0);
}})();
</script>"""

# ── WebSocket client registry ─────────────────────────────────────────────────
_ws_clients: set = set()
_ws_lock = threading.Lock()


def push_to_lan_clients(js_call: str) -> None:
    """Broadcast a JS call string to all connected LAN WebSocket clients."""
    with _ws_lock:
        dead = set()
        for ws in _ws_clients:
            try:
                ws.send(js_call)
            except Exception:
                dead.add(ws)
        _ws_clients -= dead


# ── Flask application ─────────────────────────────────────────────────────────
_app  = Flask(__name__)
_sock = Sock(_app)
_api  = None   # injected by start_server()


@_app.route("/")
def index():
    try:
        html = (UI_DIR / "index.html").read_text(encoding="utf-8")
        patched = html.replace("</body>", _build_shim() + "\n</body>", 1)
        return patched, 200, {"Content-Type": "text/html; charset=utf-8"}
    except Exception as exc:
        import traceback
        traceback.print_exc()
        return f"<pre>Error: {exc}</pre>", 500


@_app.post("/api/<method>")
def api_call(method: str):
    if _api is None:
        return jsonify({"error": "not ready"}), 503
    fn = getattr(_api, method, None)
    if fn is None:
        return jsonify({"error": "unknown method"}), 404
    args = request.get_json(silent=True) or {}
    try:
        if method == "send_message":
            result = fn(args["text"])
        elif method == "save_settings":
            result = fn(args["cfg"])
        else:
            result = fn()
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    return jsonify(result)


@_sock.route("/ws")
def ws_handler(ws):
    with _ws_lock:
        _ws_clients.add(ws)
    try:
        while True:
            ws.receive()   # block; client never sends upstream, just hold the thread
    except Exception:
        pass
    finally:
        with _ws_lock:
            _ws_clients.discard(ws)


# ── Public API ────────────────────────────────────────────────────────────────

def _get_lan_ip() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]


def start_server(api_instance) -> None:
    """Start the LAN server in a background daemon thread. Non-blocking."""
    global _api
    _api = api_instance
    ip = _get_lan_ip()
    print(f"[LAN] http://{ip}:{LAN_PORT}", flush=True)
    t = threading.Thread(
        target=_app.run,
        kwargs={
            "host": "0.0.0.0",
            "port": LAN_PORT,
            "threaded": True,
            "use_reloader": False,
        },
        daemon=True,
    )
    t.start()
