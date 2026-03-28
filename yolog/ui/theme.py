# -*- coding: utf-8 -*-
"""
ui/theme.py — Sistem de teme și factory de widget-uri
"""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk
import logging

logger = logging.getLogger(__name__)

THEMES = {
    "Dark Blue (implicit)": {
        "bg": "#0d1117", "fg": "#e6edf3", "accent": "#1f6feb",
        "entry_bg": "#161b22", "header_bg": "#010409",
        "btn_bg": "#21262d", "btn_fg": "#f0f6fc",
        "led_on": "#3fb950", "led_off": "#f85149",
        "warn": "#d29922", "ok": "#3fb950", "err": "#f85149",
        "dup_bg": "#3d1a1a", "mult_bg": "#1a3d1a", "spec_bg": "#1a1a3d",
        "alt": "#0d1f2d", "gold": "#ffd700", "cyan": "#58a6ff",
    },
    "Dark Green": {
        "bg": "#0a0f0a", "fg": "#d0f0d0", "accent": "#00aa44",
        "entry_bg": "#0f1a0f", "header_bg": "#050a05",
        "btn_bg": "#1a2e1a", "btn_fg": "#d0f0d0",
        "led_on": "#00ff66", "led_off": "#ff4444",
        "warn": "#ccaa00", "ok": "#00cc44", "err": "#ff4444",
        "dup_bg": "#3d1a1a", "mult_bg": "#1a3d1a", "spec_bg": "#1a2a3d",
        "alt": "#0f200f", "gold": "#aaff44", "cyan": "#44ffaa",
    },
    "Dark Red": {
        "bg": "#0f0a0a", "fg": "#f0d0d0", "accent": "#cc2200",
        "entry_bg": "#1a0f0f", "header_bg": "#0a0505",
        "btn_bg": "#2e1a1a", "btn_fg": "#f0d0d0",
        "led_on": "#ff6644", "led_off": "#888888",
        "warn": "#ff9900", "ok": "#ff6600", "err": "#ff2200",
        "dup_bg": "#3d1010", "mult_bg": "#1a2a1a", "spec_bg": "#1a1a3d",
        "alt": "#200f0f", "gold": "#ffaa44", "cyan": "#ff8844",
    },
    "Dark Purple": {
        "bg": "#0d0a14", "fg": "#e0d0f0", "accent": "#7c3aed",
        "entry_bg": "#160f22", "header_bg": "#08050f",
        "btn_bg": "#221a30", "btn_fg": "#e0d0f0",
        "led_on": "#a855f7", "led_off": "#f85149",
        "warn": "#d29922", "ok": "#a855f7", "err": "#f85149",
        "dup_bg": "#3d1a2a", "mult_bg": "#1a1a3d", "spec_bg": "#2a1a3d",
        "alt": "#150a20", "gold": "#d4a0ff", "cyan": "#a78bfa",
    },
    "Light (Zi)": {
        "bg": "#f0f4f8", "fg": "#1a1a2e", "accent": "#1565c0",
        "entry_bg": "#ffffff", "header_bg": "#dce8f5",
        "btn_bg": "#90a4ae", "btn_fg": "#ffffff",
        "led_on": "#2e7d32", "led_off": "#c62828",
        "warn": "#e65100", "ok": "#2e7d32", "err": "#c62828",
        "dup_bg": "#ffcdd2", "mult_bg": "#c8e6c9", "spec_bg": "#e3f2fd",
        "alt": "#e8f0f8", "gold": "#e65100", "cyan": "#0277bd",
    },
    "Light Sepia": {
        "bg": "#f5f0e8", "fg": "#2c1a00", "accent": "#8b4513",
        "entry_bg": "#fffdf5", "header_bg": "#e8dcc8",
        "btn_bg": "#b8956a", "btn_fg": "#ffffff",
        "led_on": "#4a7c2f", "led_off": "#c0392b",
        "warn": "#e67e22", "ok": "#4a7c2f", "err": "#c0392b",
        "dup_bg": "#f5c6cb", "mult_bg": "#c3e6cb", "spec_bg": "#d4edda",
        "alt": "#ede8dc", "gold": "#8b4513", "cyan": "#5c6bc0",
    },
}

# Tema activă — dict mutable, actualizat de App
TH: dict = dict(THEMES["Dark Blue (implicit)"])


def apply_theme(theme_name: str, custom_colors: dict | None = None) -> None:
    """Aplică o temă în TH global. Opțional suprascrie cu culori custom."""
    global TH
    base = dict(THEMES.get(theme_name, THEMES["Dark Blue (implicit)"]))
    if custom_colors:
        base.update({k: v for k, v in custom_colors.items() if k in base})
    TH.update(base)


def setup_ttk_style(font: tuple) -> None:
    """Configurează stilul ttk.Treeview și Combobox cu tema curentă."""
    s = ttk.Style()
    try:
        s.theme_use('clam')
    except Exception:
        pass
    s.configure("Treeview",
                 background=TH["entry_bg"], foreground=TH["fg"],
                 fieldbackground=TH["entry_bg"], font=font, rowheight=22)
    s.configure("Treeview.Heading",
                 background=TH["header_bg"], foreground=TH["fg"],
                 font=(font[0], font[1], "bold"))
    s.map("Treeview", background=[("selected", TH["accent"])])
    s.configure("TCombobox",
                 fieldbackground=TH["entry_bg"],
                 background=TH["btn_bg"],
                 foreground=TH["fg"],
                 selectbackground=TH["accent"])


class UIFactory:
    """Factory de widget-uri tematizate — elimină repetarea parametrilor de stil."""

    def __init__(self, font: tuple):
        self.fn = font
        self.fb = (font[0], font[1], "bold")

    def label(self, parent, text="", bold=False, color=None, **kw) -> tk.Label:
        return tk.Label(parent, text=text,
                        bg=TH["bg"], fg=color or TH["fg"],
                        font=self.fb if bold else self.fn, **kw)

    def entry(self, parent, width=12, color=None, justify="left", **kw) -> tk.Entry:
        return tk.Entry(parent, width=width,
                        bg=TH["entry_bg"], fg=color or TH["fg"],
                        font=self.fn, insertbackground=TH["fg"],
                        justify=justify, **kw)

    def button(self, parent, text="", cmd=None, color=None,
               width=0, **kw) -> tk.Button:
        kw_extra = {"width": width} if width > 0 else {}
        return tk.Button(parent, text=text, command=cmd,
                         bg=color or TH["btn_bg"],
                         fg="white",
                         font=self.fn,
                         relief="raised", bd=1,
                         activebackground=color or TH["btn_bg"],
                         activeforeground="white",
                         cursor="hand2",
                         **kw_extra, **kw)

    def frame(self, parent, **kw) -> tk.Frame:
        return tk.Frame(parent, bg=TH["bg"], **kw)

    def lframe(self, parent, text="", **kw) -> tk.LabelFrame:
        return tk.LabelFrame(parent, text=text,
                             bg=TH["bg"], fg=TH["fg"],
                             font=self.fn, **kw)

    def combobox(self, parent, values=None, width=8, **kw) -> ttk.Combobox:
        return ttk.Combobox(parent, values=values or [],
                            state="readonly", width=width,
                            font=self.fn, **kw)