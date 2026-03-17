"""Claude API backend — intent detection + natural language reply."""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path

from anthropic import Anthropic

from . import config as cfg_mod

# ── 日志配置 ──────────────────────────────────────────────────────────────────
_LOG_PATH = Path(__file__).parent.parent / "chat.log"
logging.basicConfig(
    filename=_LOG_PATH,
    level=logging.DEBUG,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
    encoding="utf-8",
    force=True,
)
_log = logging.getLogger("handler")

# Intent labels
INTENT_START   = "start_hand"
INTENT_STOP    = "stop_hand"
INTENT_GESTURE = "gesture"
INTENT_CHAT    = "chat"

# 若 AI 回 chat 但消息含这些词，强制重试一次确认是否为手势
_GESTURE_HINTS = re.compile(
    r"手势|比|做个|来个|摆|伸|握|张|弯|点赞|耶|yeah|ok|❤|心|枪|赞|拇指|"
    r"食指|中指|无名|小指|剪刀|胜利|兰花|摇滚|拳|掌|pose|造型",
    re.IGNORECASE,
)

_RETRY_SUFFIX = (
    "\n\n【注意】上一条消息可能是手势指令。"
    "如果用户是在要求灵巧手做某个动作，请输出 intent=\"gesture\" 并给出 positions；"
    "只有确认是纯聊天才输出 intent=\"chat\"。"
)


def _strip_fences(text: str) -> str:
    text = text.strip()
    match = re.search(r"```(?:\w*)\s*([\s\S]*?)```", text)
    if match:
        return match.group(1).strip()
    return text


def _parse(raw: str) -> tuple[str, str, dict]:
    data   = json.loads(_strip_fences(raw))
    intent = str(data.get("intent", INTENT_CHAT))
    reply  = str(data.get("reply",  raw))
    extra: dict = {}
    if intent == INTENT_GESTURE:
        if "gestures" in data:
            # 多手势序列
            extra["gestures"] = [
                {
                    "name":      str(g.get("name", f"手势{i+1}")),
                    "positions": [int(v) for v in g.get("positions", [0] * 6)],
                }
                for i, g in enumerate(data["gestures"])
            ]
        else:
            # 单手势
            extra["positions"] = [int(v) for v in data.get("positions", [0] * 6)]
    return intent, reply, extra


class ChatHandler:
    def __init__(self) -> None:
        cfg = cfg_mod.load()
        self.client = Anthropic(api_key=cfg["api_key"], base_url=cfg["base_url"])
        self.model  = cfg["model"]
        self.system = cfg["system_prompt"]
        self.history: list[dict[str, str]] = []

    def send(self, text: str) -> tuple[str, str, dict]:
        """Returns (intent, reply_text, extra)."""
        _log.info("━━━ 用户输入: %s", text)
        self.history.append({"role": "user", "content": text})

        intent, reply, extra, raw_json = self._call(self.history, label="第1次")

        # 若判为 chat 但消息含手势关键词，用加强提示重试一次
        if intent == INTENT_CHAT and _GESTURE_HINTS.search(text):
            _log.info("  → chat 但含手势关键词，触发重试")
            retry_history = self.history[:-1] + [
                {"role": "user", "content": text + _RETRY_SUFFIX}
            ]
            intent2, reply2, extra2, raw_json2 = self._call(retry_history, label="第2次(重试)")
            if intent2 == INTENT_GESTURE:
                intent, reply, extra, raw_json = intent2, reply2, extra2, raw_json2
                _log.info("  → 重试成功，修正为 gesture")
            else:
                _log.info("  → 重试仍为 %s，保持原结果", intent2)

        _log.info("  最终 intent=%s  positions=%s", intent, extra.get("positions"))
        # 存完整 JSON 到 history，防止模型看到纯文本后跟着输出纯文本
        self.history.append({"role": "assistant", "content": raw_json})
        return intent, reply, extra

    def _call(self, messages: list[dict], label: str = "") -> tuple[str, str, dict, str]:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=self.system,
            messages=messages,
        )
        raw = next(b.text for b in response.content if hasattr(b, "text"))
        _log.debug("  [%s] 原始返回: %s", label, raw.replace("\n", "\\n"))
        try:
            intent, reply, extra = _parse(raw)
            _log.info("  [%s] intent=%s  positions=%s", label, intent, extra.get("positions"))
            return intent, reply, extra, raw
        except (json.JSONDecodeError, AttributeError, ValueError) as e:
            _log.warning("  [%s] JSON解析失败(%s): %s", label, e, raw[:120])
            return INTENT_CHAT, raw, {}, raw

    def clear(self) -> None:
        self.history.clear()
