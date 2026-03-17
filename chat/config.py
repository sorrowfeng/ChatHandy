"""Persistent configuration — load from / save to config.json."""
from __future__ import annotations

import json
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent.parent / "config.json"

_DEFAULTS: dict = {
    "api_key": "",
    "base_url": "",
    "model": "",
    "system_prompt": (
        "你是一个智能助手，可以控制灵巧手设备，也可以进行日常对话。\n\n"
        "对每条用户消息，必须以 JSON 格式回复，结构如下：\n"
        "{\"intent\": \"<意图>\", \"reply\": \"<自然语言回复>\"}\n\n"
        "意图规则（根据语义判断，不限于固定词语）：\n"
        "- \"start_hand\" : 用户想要 启动 / 开启 / 运行 / 打开 灵巧手\n"
        "- \"stop_hand\"  : 用户想要 停止 / 关闭 / 暂停 / 退出 灵巧手\n"
        "- \"chat\"       : 其他所有情况（普通聊天、提问等）\n\n"
        "reply 字段：用自然中文回复用户，语气轻松友好。\n"
        "只输出 JSON，不要有任何其他内容。"
    ),
}


def load() -> dict:
    """Return config merged with defaults. Writes defaults on first run."""
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            stored = json.load(f)
        return {**_DEFAULTS, **stored}
    save(_DEFAULTS.copy())
    return _DEFAULTS.copy()


def save(cfg: dict) -> None:
    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
