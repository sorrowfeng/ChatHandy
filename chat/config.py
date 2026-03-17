"""Persistent configuration — load from / save to config.json."""
from __future__ import annotations

import json
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent.parent / "config.json"

DEFAULT_GESTURES: list[dict] = [
    {"name": "张开/伸直",       "positions": [0,    0,     0,     0,     0,     0    ]},
    {"name": "握拳",            "positions": [5000, 10000, 10000, 10000, 10000, 10000]},
    {"name": "竖大拇指/点赞",   "positions": [8000, 0,     10000, 10000, 10000, 10000]},
    {"name": "耶/比耶/剪刀手",  "positions": [0,    10000, 0,     0,     10000, 10000]},
    {"name": "食指伸出",        "positions": [0,    10000, 0,     10000, 10000, 10000]},
    {"name": "OK",              "positions": [5000, 5000,  5000,  0,     0,     0    ]},
    {"name": "比心",            "positions": [10000,3000,  3000,  10000, 10000, 10000]},
    {"name": "兰花指",          "positions": [5000, 5000,  5000,  5000,  10000, 0    ]},
    {"name": "枪手势",          "positions": [0,    0,     0,     10000, 10000, 10000]},
    {"name": "摇滚手势",        "positions": [0,    10000, 0,     10000, 10000, 0    ]},
]

_SYSTEM_PROMPT_TEMPLATE = (
    "你是一个控制灵巧手的智能助手。\n\n"
    "每条消息必须以 JSON 格式回复：\n"
    '{{"intent": "<意图>", "reply": "<自然语言回复>", ...}}\n\n'
    "━━━ 意图分类规则 ━━━\n"
    '- "start_hand" : 启动 / 开启 / 运行 / 打开 灵巧手\n'
    '- "stop_hand"  : 停止 / 关闭 / 断开 灵巧手\n'
    '- "gesture"    : 【凡是】涉及手势、动作、手指运动、摆出某个造型的请求，一律归为 gesture\n'
    '- "chat"       : 仅限与手势/设备完全无关的纯聊天\n\n'
    "【重要规则】\n"
    '1. 只要用户意图是让手做任何动作，必须输出 intent="gesture"，不得输出 chat。\n'
    "2. 「点赞」「比心」「耶」「OK」等永远指手势动作，不是社交反馈。\n"
    "3. 即使上下文是聊天，只要当前消息含手势动作含义，就输出 gesture。\n\n"
    "━━━ 单个手势格式 ━━━\n"
    '{{"intent": "gesture", "reply": "...", "positions": [p1,p2,p3,p4,p5,p6]}}\n\n'
    "━━━ 多手势序列格式（用户要求多个手势时使用）━━━\n"
    '{{"intent": "gesture", "reply": "...", "gestures": [\n'
    '  {{"name": "手势名", "positions": [p1,p2,p3,p4,p5,p6]}},\n'
    '  {{"name": "手势名", "positions": [p1,p2,p3,p4,p5,p6]}}\n'
    "]}}\n\n"
    "━━━ positions 字段 ━━━\n"
    "6 个整数，范围 0-10000：\n"
    "[大拇指侧摆, 大拇指弯曲, 食指弯曲, 中指弯曲, 无名指弯曲, 小拇指弯曲]\n"
    "- 弯曲轴：0 = 完全伸直，10000 = 完全弯曲\n"
    "- 大拇指侧摆：0 = 与手掌平行，10000 = 垂直于掌心\n\n"
    "━━━ 已配置手势参考表 ━━━\n"
    "{gesture_table}\n\n"
    "━━━ 其他规则 ━━━\n"
    "- reply 用自然中文，语气轻松\n"
    "- 非 gesture 意图时省略 positions/gestures 字段\n"
    "- 只输出 JSON，不要有任何其他内容"
)

_DEFAULTS: dict = {
    "api_key":      "",
    "base_url":     "",
    "model":        "",
    "gestures":     DEFAULT_GESTURES,
    "system_prompt": "",   # 留空时由 build_system_prompt() 自动生成
}


def build_system_prompt(gestures: list[dict]) -> str:
    """根据手势列表生成 system prompt。"""
    rows = "\n".join(
        f"- {g['name']}：{g['positions']}"
        for g in gestures
    )
    return _SYSTEM_PROMPT_TEMPLATE.format(gesture_table=rows)


def load() -> dict:
    """Return config merged with defaults. Writes defaults on first run."""
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            stored = json.load(f)
        cfg = {**_DEFAULTS, **stored}
    else:
        cfg = _DEFAULTS.copy()
        save(cfg)

    # system_prompt 为空时自动生成
    if not cfg.get("system_prompt", "").strip():
        cfg["system_prompt"] = build_system_prompt(cfg.get("gestures", DEFAULT_GESTURES))

    return cfg


def save(cfg: dict) -> None:
    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

