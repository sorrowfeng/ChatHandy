"""Settings dialog — edit and persist API configuration."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from . import config as cfg_mod

FONT = "Microsoft YaHei UI"

BG        = "#F0F2F5"
SURFACE   = "#FFFFFF"
ACCENT    = "#1D6BE8"
HOVER     = "#1558C0"
BORDER    = "#E0E6F0"
TEXT_MAIN = "#1A1A1A"
TEXT_HINT = "#888888"


class SettingsDialog(ctk.CTkToplevel):
    """Modal settings window."""

    def __init__(self, parent: ctk.CTk, on_save: Callable[[dict], None] | None = None) -> None:
        super().__init__(parent)
        self.title("设置")
        self.geometry("500x580")
        self.resizable(False, False)
        self.configure(fg_color=BG)
        self.grab_set()          # modal — block parent window
        self.lift()
        self.focus_force()

        self._on_save = on_save
        self._entries: dict[str, ctk.CTkEntry | ctk.CTkTextbox] = {}

        cfg = cfg_mod.load()
        self._build(cfg)
        self._center(parent)

    # ── Layout ───────────────────────────────────────────────────────────────

    def _build(self, cfg: dict) -> None:
        # ── Header ──
        header = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=0, height=54)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(
            header,
            text="⚙  参数设置",
            font=ctk.CTkFont(family=FONT, size=15, weight="bold"),
            text_color=TEXT_MAIN,
        ).pack(side="left", padx=20, pady=14)

        # ── Scrollable fields ──
        scroll = ctk.CTkScrollableFrame(self, fg_color=BG, corner_radius=0)
        scroll.pack(fill="both", expand=True)

        self._add_entry(scroll, "api_key",       "API Key",   cfg, secret=True)
        self._add_entry(scroll, "base_url",       "Base URL",  cfg)
        self._add_entry(scroll, "model",          "模型",      cfg)
        self._add_textbox(scroll, "system_prompt", "系统提示词", cfg)

        # ── Bottom button bar ──
        bar = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=0, height=62)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        ctk.CTkButton(
            bar, text="保存", width=110, height=38,
            corner_radius=10,
            fg_color=ACCENT, hover_color=HOVER,
            font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
            command=self._save,
        ).pack(side="right", padx=16, pady=12)

        ctk.CTkButton(
            bar, text="取消", width=90, height=38,
            corner_radius=10,
            fg_color="#EEEFF2", text_color="#666666",
            hover_color="#E0E2E5",
            font=ctk.CTkFont(family=FONT, size=13),
            command=self.destroy,
        ).pack(side="right", padx=(0, 6), pady=12)

    def _add_entry(self, parent: ctk.CTkScrollableFrame, key: str, label: str,
                   cfg: dict, secret: bool = False) -> None:
        card = self._card(parent)

        ctk.CTkLabel(
            card, text=label,
            font=ctk.CTkFont(family=FONT, size=11),
            text_color=TEXT_HINT, anchor="w",
        ).pack(fill="x", padx=14, pady=(10, 2))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(0, 10))
        row.grid_columnconfigure(0, weight=1)

        entry = ctk.CTkEntry(
            row, height=38, corner_radius=8,
            fg_color="#F7F8FA", border_color=BORDER, border_width=1,
            font=ctk.CTkFont(family=FONT, size=12),
            text_color=TEXT_MAIN,
            show="●" if secret else "",
        )
        entry.grid(row=0, column=0, sticky="ew")
        entry.insert(0, cfg.get(key, ""))

        if secret:
            self._add_reveal_btn(row, entry)

        self._entries[key] = entry

    def _add_textbox(self, parent: ctk.CTkScrollableFrame, key: str, label: str,
                     cfg: dict) -> None:
        card = self._card(parent)

        ctk.CTkLabel(
            card, text=label,
            font=ctk.CTkFont(family=FONT, size=11),
            text_color=TEXT_HINT, anchor="w",
        ).pack(fill="x", padx=14, pady=(10, 2))

        hint = ctk.CTkLabel(
            card,
            text="必须保留 JSON 格式指令（intent / reply 字段）以确保意图识别正常工作",
            font=ctk.CTkFont(family=FONT, size=10),
            text_color="#BBBBBB", anchor="w", wraplength=420,
        )
        hint.pack(fill="x", padx=14)

        tb = ctk.CTkTextbox(
            card, height=130, corner_radius=8,
            fg_color="#F7F8FA", border_color=BORDER, border_width=1,
            font=ctk.CTkFont(family=FONT, size=12),
            text_color=TEXT_MAIN, wrap="word",
        )
        tb.pack(fill="x", padx=14, pady=(4, 12))
        tb.insert("1.0", cfg.get(key, ""))

        self._entries[key] = tb

    def _add_reveal_btn(self, parent: ctk.CTkFrame, entry: ctk.CTkEntry) -> None:
        """Toggle show/hide for secret fields."""
        showing: list[bool] = [False]

        def toggle() -> None:
            showing[0] = not showing[0]
            entry.configure(show="" if showing[0] else "●")
            btn.configure(text="🔒" if showing[0] else "👁")

        btn = ctk.CTkButton(
            parent, text="👁", width=38, height=38,
            corner_radius=8,
            fg_color="#EEEFF2", text_color="#555555",
            hover_color="#E0E2E5",
            font=ctk.CTkFont(size=14),
            command=toggle,
        )
        btn.grid(row=0, column=1, padx=(6, 0))

    @staticmethod
    def _card(parent: ctk.CTkScrollableFrame) -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, fg_color=SURFACE, corner_radius=12)
        card.pack(fill="x", padx=16, pady=(10, 0))
        return card

    # ── Actions ──────────────────────────────────────────────────────────────

    def _save(self) -> None:
        cfg: dict = {}
        for key, widget in self._entries.items():
            if isinstance(widget, ctk.CTkTextbox):
                cfg[key] = widget.get("1.0", "end").strip()
            else:
                cfg[key] = widget.get().strip()
        cfg_mod.save(cfg)
        if self._on_save:
            self._on_save(cfg)
        self.destroy()

    def _center(self, parent: ctk.CTk) -> None:
        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width()  - self.winfo_width())  // 2
        py = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{px}+{py}")
