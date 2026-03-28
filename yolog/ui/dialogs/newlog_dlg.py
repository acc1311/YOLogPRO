# -*- coding: utf-8 -*-
"""ui/dialogs/newlog_dlg.py — Dialog creare log nou"""
import re, datetime, tkinter as tk
from tkinter import ttk
from ..theme import TH
from ... import i18n

def _rg(d,p,iw,ih):
    try: sw,sh=d.winfo_screenwidth(),d.winfo_screenheight()
    except: sw,sh=1366,768
    w,h=min(iw,int(sw*.92)),min(ih,int(sh*.88))
    try: x=p.winfo_rootx()+(p.winfo_width()-w)//2; y=p.winfo_rooty()+(p.winfo_height()-h)//2
    except: x,y=(sw-w)//2,(sh-h)//2
    d.geometry(f"{w}x{h}+{max(0,x)}+{max(0,y)}")

class NewLogDialog(tk.Toplevel):
    def __init__(self, parent, contests):
        super().__init__(parent)
        self.result=None; self.contests=contests
        self.title(" Log Nou / New Log"); _rg(self,parent,440,280)
        self.configure(bg=TH["bg"]); self.transient(parent); self.grab_set()
        lo={"bg":TH["bg"],"fg":TH["fg"],"font":("Consolas",11)}
        eo={"bg":TH["entry_bg"],"fg":TH["fg"],"font":("Consolas",11),"insertbackground":TH["fg"]}

        tk.Label(self,text=" Creare Log Nou / New Log",bg=TH["bg"],fg=TH["gold"],
                 font=("Consolas",13,"bold")).pack(pady=(14,8))

        tk.Label(self,text="Concurs / Contest:",**lo).pack(anchor="w",padx=20)
        self._cid_v=tk.StringVar(value=list(contests.keys())[0])
        ttk.Combobox(self,textvariable=self._cid_v,values=list(contests.keys()),
                     state="readonly",width=28,font=("Consolas",11)).pack(padx=20,pady=4,anchor="w")

        tk.Label(self,text="Nume log / Log name:",**lo).pack(anchor="w",padx=20)
        self._name_e=tk.Entry(self,width=30,**eo)
        self._name_e.insert(0,datetime.datetime.now().strftime("%Y%m%d"))
        self._name_e.pack(padx=20,pady=4,anchor="w")

        tk.Label(self,text=" Logul curent se salvează automat!",
                 bg=TH["bg"],fg=TH["warn"],font=("Consolas",9)).pack(pady=4)

        bf=tk.Frame(self,bg=TH["bg"]); bf.pack(pady=8)
        tk.Button(bf,text=" Crează",command=self._ok,bg=TH["ok"],fg="white",
                  font=("Consolas",11,"bold")).pack(side="left",padx=6)
        tk.Button(bf,text=" Anulează",command=self.destroy,bg=TH["btn_bg"],fg="white",
                  font=("Consolas",11)).pack(side="left",padx=6)

    def _ok(self):
        cid=self._cid_v.get().strip()
        name=re.sub(r"[^a-zA-Z0-9_-]","_",self._name_e.get().strip()) or datetime.datetime.now().strftime("%Y%m%d_%H%M")
        self.result={"contest":cid,"log_id":f"{cid}__{name}"}
        self.destroy()
