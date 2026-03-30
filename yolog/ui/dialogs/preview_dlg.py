# -*- coding: utf-8 -*-
"""ui/dialogs/preview_dlg.py"""
import tkinter as tk
from tkinter import scrolledtext
from ..theme import TH
from ... import i18n

class PreviewDialog(tk.Toplevel):
    def __init__(self, parent, title_str, content, save_callback):
        super().__init__(parent)
        self.title(title_str)
        try: sw,sh=self.winfo_screenwidth(),self.winfo_screenheight()
        except: sw,sh=1366,768
        self.geometry(f"{min(780,int(sw*.92))}x{min(580,int(sh*.88))}")
        self.configure(bg=TH["bg"]); self.transient(parent)
        self._save_cb=save_callback; self._content=content
        txt=scrolledtext.ScrolledText(self,bg=TH["entry_bg"],fg=TH["fg"],font=("Consolas",10),wrap="none")
        txt.pack(fill="both",expand=True,padx=10,pady=10)
        txt.insert("1.0",content); txt.config(state="disabled")
        bf=tk.Frame(self,bg=TH["bg"]); bf.pack(pady=8)
        tk.Button(bf,text=i18n.t("save"),command=self._on_save,bg=TH["ok"],fg="white",font=("Consolas",12,"bold")).pack(side="left",padx=8)
        tk.Button(bf,text=i18n.t("cancel"),command=self.destroy,bg=TH["btn_bg"],fg="white",font=("Consolas",12)).pack(side="left",padx=8)
    def _on_save(self): self._save_cb(self._content); self.destroy()
