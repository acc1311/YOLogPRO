# -*- coding: utf-8 -*-
"""ui/dialogs/firstrun_dlg.py"""
import tkinter as tk
from tkinter import ttk
from ..theme import TH

class FirstRunDialog(tk.Toplevel):
    def __init__(self, parent, cfg):
        super().__init__(parent)
        self.result=None; self.title("YO Log PRO v19 — Configurare inițială")
        try: sw,sh=self.winfo_screenwidth(),self.winfo_screenheight()
        except: sw,sh=1366,768
        w,h=min(440,int(sw*.9)),min(440,int(sh*.85))
        self.geometry(f"{w}x{h}"); self.configure(bg=TH["bg"]); self.transient(parent); self.grab_set()
        fn=("Consolas",11); eo={"bg":TH["entry_bg"],"fg":TH["fg"],"font":fn,"insertbackground":TH["fg"]}
        tk.Label(self,text=" Bun venit la YO Log PRO v19!",bg=TH["bg"],fg=TH["accent"],font=("Consolas",14,"bold")).pack(pady=(16,8))
        tk.Label(self,text="Configurați datele stației dvs.:",bg=TH["bg"],fg=TH["fg"],font=fn).pack(pady=(0,8))
        p=tk.Frame(self,bg=TH["bg"]); p.pack(fill="x",padx=20)
        fields=[("call","Indicativ (ex: YO8ACR)",cfg.get("call","YO8ACR")),
                ("loc","Locator (ex: KN37)",cfg.get("loc","KN37")),
                ("jud","Județ (ex: NT)",cfg.get("jud","NT")),
                ("op_name","Operator",cfg.get("op_name",""))]
        self._es={}
        for k,lb,v in fields:
            tk.Label(p,text=lb,bg=TH["bg"],fg=TH["fg"],font=fn).pack(anchor="w",pady=(6,0))
            e=tk.Entry(p,width=30,**eo); e.insert(0,v); e.pack(anchor="w"); self._es[k]=e
        tk.Label(p,text="Limbă / Language:",bg=TH["bg"],fg=TH["fg"],font=fn).pack(anchor="w",pady=(8,0))
        self._lang_v=tk.StringVar(value=cfg.get("lang","ro"))
        ttk.Combobox(p,textvariable=self._lang_v,values=["ro","en"],state="readonly",width=10,font=fn).pack(anchor="w",pady=2)
        tk.Button(self,text=" Continuă",command=self._ok,bg=TH["ok"],fg="white",font=("Consolas",12,"bold")).pack(pady=16)
    def _ok(self):
        self.result={k:(self._es[k].get().strip().upper() if k in {"call","loc","jud"} else self._es[k].get().strip()) for k in self._es}
        self.result["lang"]=self._lang_v.get(); self.destroy()
