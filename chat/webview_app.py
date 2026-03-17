"""pywebview Python API — bridges JS UI and the chat/hand backend."""
from __future__ import annotations

import json
import threading
import time

import webview

from .handler import INTENT_GESTURE, INTENT_START, INTENT_STOP, ChatHandler
from .runner import CommandRunner
from . import config as cfg_mod


class Api:
    """Exposed to JS as window.pywebview.api.*"""

    def __init__(self) -> None:
        self.handler = ChatHandler()
        self.runner  = CommandRunner()

    # ── Called from JS ────────────────────────────────────────────────

    def send_message(self, text: str) -> dict:
        try:
            intent, reply, extra = self.handler.send(text)
        except Exception as exc:
            return {"intent": "chat", "reply": f"[错误] {exc}"}

        if intent == INTENT_START:
            # Return initial reply immediately; push final result via JS callback
            threading.Thread(target=self._start_hand_bg, daemon=True).start()
            return {"intent": intent, "reply": reply}

        if intent == INTENT_STOP:
            ok, msg = self.runner.stop_hand()
            return {
                "intent":      intent,
                "reply":       reply if ok else f"⚠️ {msg}",
                "hand_running": self.runner.hand_running,
            }

        if intent == INTENT_GESTURE:
            if "gestures" in extra:
                # 多手势序列：立即返回 AI 回复，后台逐个执行
                threading.Thread(
                    target=self._exec_sequence_bg,
                    args=(extra["gestures"],),
                    daemon=True,
                ).start()
                return {"intent": intent, "reply": reply, "multi": True}
            else:
                positions = extra.get("positions", [0] * 6)
                ok, msg   = self.runner.move(positions)
                return {"intent": intent, "reply": reply if ok else f"⚠️ {msg}"}

        return {"intent": intent, "reply": reply}

    def get_settings(self) -> dict:
        return cfg_mod.load()

    def check_config(self) -> dict:
        """返回缺失的必填项列表，供 JS 启动时提示。"""
        cfg = cfg_mod.load()
        missing = [f for f in ("api_key", "base_url", "model") if not cfg.get(f, "").strip()]
        return {"missing": missing}

    def save_settings(self, cfg: dict) -> bool:
        # 若 system_prompt 为空或手势列表有变化，自动重新生成
        if not cfg.get("system_prompt", "").strip():
            cfg["system_prompt"] = cfg_mod.build_system_prompt(
                cfg.get("gestures", cfg_mod.DEFAULT_GESTURES)
            )
        cfg_mod.save(cfg)
        self.handler = ChatHandler()
        return True

    def clear_chat(self) -> None:
        self.handler.clear()

    def hand_running(self) -> bool:
        return self.runner.hand_running

    # ── Internal ──────────────────────────────────────────────────────

    def _exec_sequence_bg(self, gestures: list) -> None:
        """逐个执行手势序列，每步之间等待 1.5 s 让关节运动完成。"""
        total = len(gestures)
        for i, g in enumerate(gestures):
            name      = g.get("name", f"手势{i+1}")
            positions = g.get("positions", [0] * 6)
            ok, msg   = self.runner.move(positions)
            payload   = json.dumps({
                "name":  name,
                "index": i + 1,
                "total": total,
                "ok":    ok,
                "msg":   msg,
            })
            for w in webview.windows:
                try:
                    w.evaluate_js(f"onGestureStep({payload})")
                except Exception:
                    pass
            if ok and i < total - 1:
                time.sleep(1.5)   # 等待当前手势运动完成后再执行下一个

    def _start_hand_bg(self) -> None:
        """Runs in background thread; pushes result to JS via evaluate_js.
        Must ALWAYS call onHandResult — otherwise JS stays busy forever."""
        try:
            ok, msg = self.runner.start_hand()
        except Exception as exc:
            ok, msg = False, str(exc)
        payload = json.dumps({
            "text":    f"✅ {msg}" if ok else f"❌ {msg}",
            "running": self.runner.hand_running,
        })
        for w in webview.windows:
            try:
                w.evaluate_js(f"onHandResult({payload})")
            except Exception:
                pass
