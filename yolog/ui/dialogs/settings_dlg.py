# -*- coding: utf-8 -*-
"""ui/dialogs/settings_dlg.py — Dialog setări aplicație"""
import tkinter as tk
from tkinter import ttk
from ..theme import TH
from ... import i18n

def _rg(d, p, iw, ih):
    try: sw, sh = d.winfo_screenwidth(), d.winfo_screenheight()
    except: sw, sh = 1366, 768
    w, h = min(iw, int(sw*.92)), min(ih, int(sh*.88))
    try:
        d.update_idletasks()
        x = p.winfo_rootx()+(p.winfo_width()-w)//2
        y = p.winfo_rooty()+(p.winfo_height()-h)//2
        x = max(10, min(x, sw-w-10))
        y = max(10, min(y, sh-h-10))
    except: x, y = (sw-w)//2, (sh-h)//2
    d.geometry(f"{w}x{h}+{x}+{y}")

class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, cfg):
        super().__init__(parent)
        self.result = None
        self._cfg = dict(cfg)
        self.title(i18n.t("settings"))
        _rg(self, parent, 440, 580)
        self.configure(bg=TH["bg"])
        self.transient(parent)
        self.grab_set()
        self._build()

    def _build(self):
        fn = ("Consolas", 11)
        eo = {"bg": TH["entry_bg"], "fg": TH["fg"], "font": fn, "insertbackground": TH["fg"]}
        outer = tk.Frame(self, bg=TH["bg"]); outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, bg=TH["bg"], highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y"); canvas.pack(side="left", fill="both", expand=True)
        p = tk.Frame(canvas, bg=TH["bg"])
        win = canvas.create_window((0,0), window=p, anchor="nw")
        p.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        fields = [
            ("call",     i18n.t("call"),     self._cfg.get("call", "")),
            ("loc",      i18n.t("locator"),  self._cfg.get("loc", "")),
            ("jud",      i18n.t("county"),   self._cfg.get("jud", "")),
            ("addr",     i18n.t("address"),  self._cfg.get("addr", "")),
            ("op_name",  i18n.t("op"),       self._cfg.get("op_name", "")),
            ("power",    i18n.t("power"),    self._cfg.get("power", "100")),
            ("email",    i18n.t("email_l"),  self._cfg.get("email", "")),
            ("soapbox",  i18n.t("soapbox"),  self._cfg.get("soapbox", "73 GL")),
            ("fs",       i18n.t("font_size"),str(self._cfg.get("fs", 11))),
        ]
        self._es = {}
        for k, lb, v in fields:
            tk.Label(p, text=lb, bg=TH["bg"], fg=TH["fg"], font=fn).pack(anchor="w", padx=15, pady=(6,0))
            e = tk.Entry(p, width=35, **eo); e.insert(0, v); e.pack(pady=2, padx=15)
            self._es[k] = e

        # Limbă
        tk.Label(p, text="Limbă / Language:", bg=TH["bg"], fg=TH["fg"], font=fn).pack(anchor="w", padx=15, pady=(8,0))
        self._lang_v = tk.StringVar(value=self._cfg.get("lang", "ro"))
        ttk.Combobox(p, textvariable=self._lang_v, values=["ro","en"],
                     state="readonly", width=10, font=fn).pack(padx=15, pady=2, anchor="w")

        self._snd_v = tk.BooleanVar(value=self._cfg.get("sounds", True))
        tk.Checkbutton(p, text=i18n.t("en_sounds"), variable=self._snd_v,
                       bg=TH["bg"], fg=TH["fg"], selectcolor=TH["entry_bg"],
                       activebackground=TH["bg"], font=fn).pack(anchor="w", padx=15, pady=4)

        tk.Button(p, text=i18n.t("save"), command=self._save,
                  bg=TH["accent"], fg="white", font=fn).pack(pady=12)

    def _save(self):
        result = {}
        for k, e in self._es.items():
            v = e.get().strip()
            result[k] = v.upper() if k in {"call","loc","jud"} else v
        try: result["fs"] = int(self._es["fs"].get().strip())
        except: result["fs"] = 11
        result["sounds"] = self._snd_v.get()
        result["lang"]   = self._lang_v.get()
        self.result = result
        self.destroy()
