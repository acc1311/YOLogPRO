# -*- coding: utf-8 -*-
"""ui/dialogs/timer_dlg.py — Timer concurs"""
import datetime, tkinter as tk
from tkinter import ttk
from ..theme import TH
from ... import i18n
try:
    import winsound; HAS_SND=True
except ImportError: HAS_SND=False

def _rg(d,p,iw,ih):
    try: sw,sh=d.winfo_screenwidth(),d.winfo_screenheight()
    except: sw,sh=1366,768
    w,h=min(iw,int(sw*.92)),min(ih,int(sh*.88))
    try: x=p.winfo_rootx()+(p.winfo_width()-w)//2; y=p.winfo_rooty()+(p.winfo_height()-h)//2
    except: x,y=(sw-w)//2,(sh-h)//2
    d.geometry(f"{w}x{h}+{max(0,x)}+{max(0,y)}")

class TimerDialog(tk.Toplevel):
    def __init__(self, parent, cfg=None):
        super().__init__(parent)
        self._cfg=cfg or {}; self.title(i18n.t("timer_t")); _rg(self,parent,360,340)
        self.configure(bg=TH["bg"]); self.transient(parent); self.resizable(True,True)
        self._running=False; self._end_time=None; self._duration=0
        self._elapsed_start=None; self._elapsed_secs=0; self._alerted=set()
        self._build(); self._tick()
        self.update_idletasks()
        self.geometry(f"+{parent.winfo_rootx()+(parent.winfo_width()-self.winfo_reqwidth())//2}+{parent.winfo_rooty()+(parent.winfo_height()-self.winfo_reqheight())//2}")

    def _build(self):
        lo={"bg":TH["bg"],"fg":TH["fg"],"font":("Consolas",11)}
        eo={"bg":TH["entry_bg"],"fg":TH["fg"],"font":("Consolas",11),"justify":"center","insertbackground":TH["fg"],"width":6}
        df=tk.Frame(self,bg=TH["bg"]); df.pack(pady=(14,4))
        tk.Label(df,text="Ore:",**lo).pack(side="left",padx=4)
        self._h_e=tk.Entry(df,**eo); self._h_e.insert(0,"4"); self._h_e.pack(side="left")
        tk.Label(df,text="Min:",**lo).pack(side="left",padx=(10,4))
        self._m_e=tk.Entry(df,**eo); self._m_e.insert(0,"0"); self._m_e.pack(side="left")
        self._time_lbl=tk.Label(self,text="00:00:00",bg=TH["bg"],fg=TH["gold"],font=("Consolas",34,"bold")); self._time_lbl.pack(pady=6)
        self._rem_lbl=tk.Label(self,text="",**lo); self._rem_lbl.pack()
        af=tk.LabelFrame(self,text="  Avertizări sonore ",bg=TH["bg"],fg=TH["fg"],font=("Consolas",9)); af.pack(fill="x",padx=12,pady=6)
        self._alert_v=tk.BooleanVar(value=True)
        tk.Checkbutton(af,text="Activ (5/3/1 min / Final)",variable=self._alert_v,bg=TH["bg"],fg=TH["fg"],activebackground=TH["bg"],selectcolor=TH["entry_bg"],font=("Consolas",9)).pack(anchor="w",padx=6)
        bf=tk.Frame(self,bg=TH["bg"]); bf.pack(pady=8)
        self._start_btn=tk.Button(bf,text=i18n.t("timer_start"),command=self._start,bg=TH["ok"],fg="white",font=("Consolas",11)); self._start_btn.pack(side="left",padx=4)
        tk.Button(bf,text=i18n.t("timer_reset"),command=self._reset,bg=TH["warn"],fg="white",font=("Consolas",11)).pack(side="left",padx=4)

    def _start(self):
        if self._running:
            self._running=False; self._start_btn.config(text=i18n.t("timer_start"),bg=TH["ok"])
        else:
            try: h=int(self._h_e.get() or 0); m=int(self._m_e.get() or 0); self._duration=h*3600+m*60
            except: self._duration=0
            self._alerted=set(); self._running=True; self._elapsed_start=datetime.datetime.utcnow()
            if self._duration>0: self._end_time=self._elapsed_start+datetime.timedelta(seconds=self._duration)
            else: self._end_time=None
            self._start_btn.config(text=i18n.t("timer_stop"),bg=TH["err"])

    def _reset(self):
        self._running=False; self._elapsed_secs=0; self._end_time=None; self._elapsed_start=None; self._alerted=set()
        self._time_lbl.config(text="00:00:00",fg=TH["gold"]); self._rem_lbl.config(text="")
        self._start_btn.config(text=i18n.t("timer_start"),bg=TH["ok"])

    def _beep(self, kind):
        if not self._alert_v.get() or not HAS_SND: return
        try:
            patterns={"5min":[(880,200)],"3min":[(880,200),(880,200)],"1min":[(1200,200)]*3,"end":[(1600,300)]*5}
            for freq,dur in patterns.get(kind,[]): winsound.Beep(freq,dur)
        except: pass

    def _tick(self):
        try:
            if not self.winfo_exists(): return
        except: return
        if self._running and self._elapsed_start:
            now=datetime.datetime.utcnow()
            elapsed=int((now-self._elapsed_start).total_seconds())+self._elapsed_secs
            h,rem=divmod(elapsed,3600); m,s=divmod(rem,60)
            try:
                self._time_lbl.config(text=f"{h:02d}:{m:02d}:{s:02d}")
                if self._end_time:
                    remaining=int((self._end_time-now).total_seconds())
                    if remaining<=0:
                        if "end" not in self._alerted: self._alerted.add("end"); self._beep("end")
                        self._running=False; self._time_lbl.config(fg=TH["err"])
                        self._rem_lbl.config(text=" TIME UP!",fg=TH["err"])
                        self._start_btn.config(text=i18n.t("timer_start"),bg=TH["ok"])
                    else:
                        rh,rr=divmod(remaining,3600); rm,rs=divmod(rr,60)
                        col=TH["err"] if remaining<=60 else (TH["warn"] if remaining<=180 else ("#FF9800" if remaining<=300 else TH["fg"]))
                        self._rem_lbl.config(text=f"{i18n.t('remaining')} {rh:02d}:{rm:02d}:{rs:02d}",fg=col)
                        if remaining<=60 and "1min" not in self._alerted: self._alerted.add("1min"); self._beep("1min")
                        elif remaining<=180 and "3min" not in self._alerted: self._alerted.add("3min"); self._beep("3min")
                        elif remaining<=300 and "5min" not in self._alerted: self._alerted.add("5min"); self._beep("5min")
            except: return
        try: self.after(1000,self._tick)
        except: pass
