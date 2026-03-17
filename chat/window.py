"""Main chat window — layout, events, and message orchestration."""
from __future__ import annotations

import threading

import customtkinter as ctk

from .bubble import DateDivider, MessageBubble, TypingBubble
from .handler import INTENT_GESTURE, INTENT_START, INTENT_STOP, ChatHandler
from .runner import CommandRunner
from .settings_dialog import SettingsDialog

FONT = "Microsoft YaHei UI"

# ── Palette ──────────────────────────────────────────────────────────────────
BG_COLOR     = "#F0F2F5"
SURFACE      = "#FFFFFF"
ACCENT       = "#1D6BE8"
ACCENT_HOVER = "#1558C0"
STATUS_ON    = "#07C160"
STATUS_BUSY  = "#FF9500"
STATUS_INIT  = "#9B59B6"
SEPARATOR    = "#E5E6EB"
TEXT_MAIN    = "#1A1A1A"
TEXT_MUTED   = "#666666"
HAND_ON      = "#07C160"
HAND_OFF     = "#CCCCCC"


class ChatWindow(ctk.CTk):
    """Top-level application window."""

    def __init__(self) -> None:
        super().__init__()

        self.title("ChatHandy")
        self.geometry("440x760")
        self.minsize(360, 520)
        self.configure(fg_color=BG_COLOR)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.runner = CommandRunner()

        self._build_header()
        self._build_messages()
        self._build_input()

        self.handler: ChatHandler | None = ChatHandler()
        self._add_ai_bubble(
            "你好！我是 AI 助手 😊\n"
            "• 说「启动灵巧手」初始化设备\n"
            "• 说「做个握拳手势」控制手部动作\n"
            "• 说「关闭灵巧手」断开设备"
        )

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=0, height=66)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(1, weight=1)

        # Avatar
        avatar = ctk.CTkFrame(
            header, fg_color=ACCENT, corner_radius=22, width=44, height=44
        )
        avatar.grid(row=0, column=0, padx=(16, 10), pady=11)
        avatar.grid_propagate(False)
        ctk.CTkLabel(
            avatar, text="AI", text_color=SURFACE,
            font=ctk.CTkFont(family=FONT, size=14, weight="bold"),
        ).place(relx=0.5, rely=0.5, anchor="center")

        # Name + status
        info = ctk.CTkFrame(header, fg_color="transparent")
        info.grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(
            info, text="AI 助手",
            font=ctk.CTkFont(family=FONT, size=16, weight="bold"),
            text_color=TEXT_MAIN,
        ).pack(anchor="w")
        self._status_lbl = ctk.CTkLabel(
            info, text="● 在线",
            font=ctk.CTkFont(family=FONT, size=11),
            text_color=STATUS_ON,
        )
        self._status_lbl.pack(anchor="w")

        # Right-side controls
        ctrl = ctk.CTkFrame(header, fg_color="transparent")
        ctrl.grid(row=0, column=2, padx=12)

        self._hand_lbl = ctk.CTkLabel(
            ctrl, text="⚙ 灵巧手",
            font=ctk.CTkFont(family=FONT, size=10),
            text_color=HAND_OFF,
        )
        self._hand_lbl.pack(pady=(0, 4))

        btn_row = ctk.CTkFrame(ctrl, fg_color="transparent")
        btn_row.pack()

        ctk.CTkButton(
            btn_row, text="设置", width=46, height=26, corner_radius=8,
            fg_color="#F0F2F5", text_color=TEXT_MUTED, hover_color="#E0E2E5",
            font=ctk.CTkFont(family=FONT, size=11),
            command=self._open_settings,
        ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            btn_row, text="清空", width=46, height=26, corner_radius=8,
            fg_color="#F0F2F5", text_color=TEXT_MUTED, hover_color="#E0E2E5",
            font=ctk.CTkFont(family=FONT, size=11),
            command=self._clear_chat,
        ).pack(side="left")

        ctk.CTkFrame(self, fg_color=SEPARATOR, height=1, corner_radius=0).grid(
            row=0, column=0, sticky="sew"
        )

    def _build_messages(self) -> None:
        self.msg_area = ctk.CTkScrollableFrame(
            self, fg_color=BG_COLOR, corner_radius=0
        )
        self.msg_area.grid(row=1, column=0, sticky="nsew")
        self.msg_area.grid_columnconfigure(0, weight=1)
        DateDivider(self.msg_area).pack(fill="x")

    def _build_input(self) -> None:
        ctk.CTkFrame(self, fg_color=SEPARATOR, height=1, corner_radius=0).grid(
            row=2, column=0, sticky="new"
        )
        bar = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=0, height=78)
        bar.grid(row=2, column=0, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(0, weight=1)
        bar.grid_rowconfigure(0, weight=1)

        self.input_box = ctk.CTkTextbox(
            bar, height=46, corner_radius=12,
            fg_color="#F5F6F8", border_width=0,
            font=ctk.CTkFont(family=FONT, size=13),
            text_color=TEXT_MAIN, wrap="word", activate_scrollbars=False,
        )
        self.input_box.grid(row=0, column=0, padx=(12, 8), pady=16, sticky="ew")
        self.input_box.bind("<Return>", self._on_enter)

        self.send_btn = ctk.CTkButton(
            bar, text="发送", width=66, height=46, corner_radius=12,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
            command=self._send_message,
        )
        self.send_btn.grid(row=0, column=1, padx=(0, 12), pady=16)
        self.input_box.focus_set()

    # ── Message helpers ───────────────────────────────────────────────────────

    def _add_ai_bubble(self, text: str) -> None:
        MessageBubble(self.msg_area, text, is_sent=False).pack(fill="x")
        self._scroll_bottom()

    def _add_user_bubble(self, text: str) -> None:
        MessageBubble(self.msg_area, text, is_sent=True).pack(fill="x")
        self._scroll_bottom()

    def _add_typing(self) -> TypingBubble:
        w = TypingBubble(self.msg_area)
        w.pack(fill="x")
        self._scroll_bottom()
        return w

    def _scroll_bottom(self) -> None:
        def _do() -> None:
            try:
                self.msg_area._parent_canvas.yview_moveto(1.0)
            except AttributeError:
                pass
        self.after(80, _do)

    def _update_hand_indicator(self) -> None:
        if self.runner.hand_running:
            self._hand_lbl.configure(text="⚙ 灵巧手 ●", text_color=HAND_ON)
        else:
            self._hand_lbl.configure(text="⚙ 灵巧手", text_color=HAND_OFF)

    def _set_status(self, text: str, color: str) -> None:
        self._status_lbl.configure(text=text, text_color=color)

    def _set_ui_busy(self, busy: bool) -> None:
        self.send_btn.configure(state="disabled" if busy else "normal")
        if not busy:
            self._set_status("● 在线", STATUS_ON)
            self.input_box.focus_set()

    # ── Events ────────────────────────────────────────────────────────────────

    def _on_enter(self, event) -> str:
        if event.state & 0x1:   # Shift+Enter → newline
            return ""
        self._send_message()
        return "break"

    def _send_message(self) -> None:
        if self.handler is None:
            return
        text = self.input_box.get("1.0", "end").strip()
        if not text:
            return

        self.input_box.delete("1.0", "end")
        self._set_ui_busy(True)
        self._set_status("● 正在回复…", STATUS_BUSY)

        self._add_user_bubble(text)
        typing = self._add_typing()

        def worker() -> None:
            try:
                result = self.handler.send(text)  # type: ignore[union-attr]
            except Exception as exc:
                result = (INTENT_CHAT, f"[错误] {exc}", {})
            self.after(0, lambda: self._on_reply(typing, result))

        threading.Thread(target=worker, daemon=True).start()

    def _on_reply(
        self,
        typing: TypingBubble,
        result: tuple[str, str, dict],
    ) -> None:
        intent, reply, extra = result
        typing.destroy()

        if intent == INTENT_START:
            # Show "starting" bubble immediately, then init in background
            self._add_ai_bubble(reply)
            self._set_status("● 正在初始化…", STATUS_INIT)
            threading.Thread(target=self._do_start_hand, daemon=True).start()
            return  # send_btn stays disabled until init done

        elif intent == INTENT_STOP:
            ok, msg = self.runner.stop_hand()
            self._add_ai_bubble(reply if ok else f"⚠️ {msg}")
            self._update_hand_indicator()

        elif intent == INTENT_GESTURE:
            positions = extra.get("positions", [0] * 6)
            ok, msg = self.runner.move(positions)
            if ok:
                self._add_ai_bubble(reply)
            else:
                self._add_ai_bubble(f"⚠️ {msg}")

        else:
            self._add_ai_bubble(reply)

        self._set_ui_busy(False)

    def _do_start_hand(self) -> None:
        """Run in background thread — blocks ~5s for homing."""
        ok, msg = self.runner.start_hand()
        bubble_text = f"✅ {msg}" if ok else f"❌ {msg}"
        self.after(0, lambda: self._add_ai_bubble(bubble_text))
        self.after(0, self._update_hand_indicator)
        self.after(0, lambda: self._set_ui_busy(False))

    # ── Settings ──────────────────────────────────────────────────────────────

    def _open_settings(self) -> None:
        SettingsDialog(self, on_save=self._on_settings_saved)

    def _on_settings_saved(self, _cfg: dict) -> None:
        self.handler = ChatHandler()
        self._add_ai_bubble("设置已保存，配置已生效 ✅")

    def _clear_chat(self) -> None:
        if self.handler:
            self.handler.clear()
        for w in self.msg_area.winfo_children():
            w.destroy()
        DateDivider(self.msg_area).pack(fill="x")
        self._add_ai_bubble("对话已清空，有什么可以帮你的吗？😊")
