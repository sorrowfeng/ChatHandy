"""Message bubble widgets for the chat UI."""
from __future__ import annotations

import tkinter as tk
from datetime import datetime
from typing import Optional

import customtkinter as ctk

# Segoe UI 在 Windows 10/11 上会自动回退到：
#   中文 → Microsoft YaHei / SimSun
#   emoji → Segoe UI Emoji（完整显示，Tk 8.6 下单色）
FONT      = "Segoe UI"
FONT_SIZE = 11
BUBBLE_W  = 24      # tk.Text 宽度（字符数），约 ~215 px


class MessageBubble(ctk.CTkFrame):
    """单条聊天消息气泡（可选中复制，emoji 完整显示）。"""

    SENT_BG = "#1D6BE8"
    SENT_FG = "#FFFFFF"
    RECV_BG = "#FFFFFF"
    RECV_FG = "#1A1A1A"
    TIME_FG = "#AAAAAA"

    def __init__(self, parent: ctk.CTkFrame, text: str, is_sent: bool, **kwargs) -> None:
        super().__init__(parent, fg_color="transparent", **kwargs)

        now    = datetime.now().strftime("%H:%M")
        bg     = self.SENT_BG if is_sent else self.RECV_BG
        fg     = self.SENT_FG if is_sent else self.RECV_FG
        sel_bg = "#5590F0"    if is_sent else "#B0C8F0"
        side   = "right"      if is_sent else "left"
        anchor = "e"          if is_sent else "w"

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(4, 0))

        col = ctk.CTkFrame(row, fg_color="transparent")
        col.pack(side=side)

        bubble = ctk.CTkFrame(col, fg_color=bg, corner_radius=16)
        bubble.pack(anchor=anchor)

        txt = tk.Text(
            bubble,
            wrap="word",
            width=BUBBLE_W,
            height=1,
            bg=bg,
            fg=fg,
            font=(FONT, FONT_SIZE),
            relief="flat",
            bd=0,
            padx=12,
            pady=8,
            cursor="arrow",
            insertwidth=0,
            selectbackground=sel_bg,
            selectforeground=fg,
            highlightthickness=0,
            spacing1=1,
            spacing3=1,
        )
        txt.insert("1.0", text)
        txt.configure(state="disabled")
        txt.pack()

        # <Map> 在组件首次显示时触发，此时 displaylines 计算准确
        def _on_map(e=None):
            try:
                txt.update_idletasks()
                res = txt.count("1.0", "end-1c", "displaylines")
                h = res[0] if res else 1
                txt.configure(height=max(1, h))
            except Exception:
                h = txt.get("1.0", "end-1c").count("\n") + 1
                txt.configure(height=max(1, h))
            txt.unbind("<Map>")

        txt.bind("<Map>", _on_map)

        # Ctrl+C 与右键菜单
        def _copy(event=None):
            try:
                sel = txt.get(tk.SEL_FIRST, tk.SEL_LAST)
            except tk.TclError:
                sel = txt.get("1.0", "end-1c")
            txt.clipboard_clear()
            txt.clipboard_append(sel)
            return "break"

        txt.bind("<Control-c>", _copy)
        txt.bind("<Control-C>", _copy)
        _attach_menu(txt, _copy)

        ctk.CTkLabel(
            col,
            text=now,
            text_color=self.TIME_FG,
            font=ctk.CTkFont(family=FONT, size=9),
        ).pack(anchor=anchor, pady=(2, 0))


def _attach_menu(txt: tk.Text, copy_fn) -> None:
    menu = tk.Menu(
        txt, tearoff=0,
        font=(FONT, 10),
        bg="#FFFFFF", fg="#1A1A1A",
        activebackground="#1D6BE8", activeforeground="#FFFFFF",
    )

    def copy_all():
        txt.clipboard_clear()
        txt.clipboard_append(txt.get("1.0", "end-1c"))

    menu.add_command(label="复制选中", command=copy_fn)
    menu.add_command(label="复制全部", command=copy_all)

    def show(event):
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    txt.bind("<Button-3>", show)


class TypingBubble(ctk.CTkFrame):
    """AI 正在输入的动画气泡。"""

    _FRAMES = ["●  ○  ○", "●  ●  ○", "●  ●  ●", "○  ●  ●", "○  ○  ●"]

    def __init__(self, parent: ctk.CTkFrame, **kwargs) -> None:
        super().__init__(parent, fg_color="transparent", **kwargs)

        self._idx = 0
        self._after_id: Optional[str] = None

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(4, 0))

        bubble = ctk.CTkFrame(row, fg_color="#FFFFFF", corner_radius=16)
        bubble.pack(side="left")

        self._dot = ctk.CTkLabel(
            bubble,
            text=self._FRAMES[0],
            text_color="#C0C0C0",
            font=ctk.CTkFont(family=FONT, size=10),
            padx=12,
            pady=8,
        )
        self._dot.pack()
        self._animate()

    def _animate(self) -> None:
        self._idx = (self._idx + 1) % len(self._FRAMES)
        try:
            self._dot.configure(text=self._FRAMES[self._idx])
            self._after_id = self.after(280, self._animate)
        except Exception:
            pass

    def destroy(self) -> None:
        if self._after_id:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
        super().destroy()


class DateDivider(ctk.CTkFrame):
    """消息列表顶部的日期分隔线。"""

    def __init__(self, parent: ctk.CTkFrame, **kwargs) -> None:
        super().__init__(parent, fg_color="transparent", **kwargs)

        now = datetime.now().strftime("%Y年%m月%d日  %H:%M")
        ctk.CTkLabel(
            self,
            text=now,
            text_color="#BBBBBB",
            font=ctk.CTkFont(family=FONT, size=9),
        ).pack(pady=8)
