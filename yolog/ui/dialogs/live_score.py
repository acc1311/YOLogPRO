# -*- coding: utf-8 -*-
"""ui/dialogs/live_score.py — Panou Scor Live"""
import datetime, tkinter as tk
from tkinter import ttk
from collections import Counter
from ..theme import TH
from ...core.score import Score
from ...core.dxcc import DXCC
from ...core.bands import BANDS_ALL

class LiveScorePanel(tk.Toplevel):
    def __init__(self, parent, log_getter, cfg_getter, contest_getter):
        super().__init__(parent)
        self.log_getter=log_getter; self.cfg_getter=cfg_getter; self.contest_getter=contest_getter
        self.title(" Scor Live — YO Log PRO v19")
        try: sw,sh=self.winfo_screenwidth(),self.winfo_screenheight()
        except: sw,sh=1366,768
        self.geometry(f"440x{min(520,int(sh*.88))}")
        self.configure(bg=TH["bg"]); self.resizable(False,True)
        self._build(); self._refresh(); self._schedule()

    def _build(self):
        tk.Label(self,text=" Scor Contest Live",bg=TH["header_bg"],fg=TH["gold"],
                 font=("Consolas",13,"bold"),pady=6).pack(fill="x")
        mf=tk.Frame(self,bg=TH["bg"],padx=12,pady=8); mf.pack(fill="both",expand=True)
        self._score_lbl=tk.Label(mf,text="0",bg=TH["bg"],fg=TH["gold"],font=("Consolas",36,"bold")); self._score_lbl.pack(pady=(10,0))
        tk.Label(mf,text="SCOR TOTAL",bg=TH["bg"],fg=TH["fg"],font=("Consolas",9)).pack()
        tk.Frame(mf,bg=TH["accent"],height=1).pack(fill="x",pady=8)
        stats_grid=tk.Frame(mf,bg=TH["bg"]); stats_grid.pack(fill="x")
        self._stat_widgets={}
        for key,label,row,col in [("qso_total","Total QSO",0,0),("qso_pts","Puncte QSO",0,1),("mults","Multiplicatori",1,0),("dxcc","DXCC",1,1),("rate_1h","QSO/h (1h)",2,0),("rate_10","QSO/h (10min)",2,1),("unique","Indicative unice",3,0),("countries","Țări lucrate",3,1)]:
            frm=tk.Frame(stats_grid,bg=TH["bg"],bd=1,relief="flat",padx=10,pady=6); frm.grid(row=row,column=col,padx=4,pady=3,sticky="ew"); stats_grid.columnconfigure(col,weight=1)
            tk.Label(frm,text=label,bg=TH["bg"],fg=TH["fg"],font=("Consolas",8)).pack(anchor="w")
            val_lbl=tk.Label(frm,text="0",bg=TH["bg"],fg=TH["cyan"],font=("Consolas",14,"bold")); val_lbl.pack(anchor="w"); self._stat_widgets[key]=val_lbl
        tk.Frame(mf,bg=TH["accent"],height=1).pack(fill="x",pady=8)
        tk.Label(mf,text="QSO per bandă:",bg=TH["bg"],fg=TH["fg"],font=("Consolas",9,"bold")).pack(anchor="w")
        self._band_frame=tk.Frame(mf,bg=TH["bg"]); self._band_frame.pack(fill="x",pady=4)
        self._upd_lbl=tk.Label(self,text="",bg=TH["bg"],fg=TH["fg"],font=("Consolas",8)); self._upd_lbl.pack(side="bottom",anchor="e",padx=6,pady=2)
        tk.Button(self,text="R Refresh",command=self._refresh,bg=TH["btn_bg"],fg="white",font=("Consolas",9)).pack(side="bottom",pady=4)

    def _refresh(self):
        log=self.log_getter(); cfg=self.cfg_getter(); cc=self.contest_getter(); now=datetime.datetime.utcnow()
        qp,mc,tot=Score.total(log,cc,cfg); self._score_lbl.config(text=str(tot))
        unique_calls=len(set(q.get("c","") for q in log))
        countries=len(set(DXCC.lookup(q.get("c",""))[0] for q in log if q.get("c")))
        dxcc_count=len(set(DXCC.lookup(q.get("c",""))[1] for q in log if q.get("c")))
        def _in(q,mins):
            try:
                dt=datetime.datetime.strptime((q.get("d","")+" "+q.get("t","00:00")).strip(),"%Y-%m-%d %H:%M")
                return (now-dt).total_seconds()<=mins*60
            except: return False
        rate_1h=sum(1 for q in log if _in(q,60)); rate_10=sum(1 for q in log if _in(q,10))*6
        for k,v in [("qso_total",str(len(log))),("qso_pts",str(qp)),("mults",str(mc)),("dxcc",str(dxcc_count)),("rate_1h",str(rate_1h)),("rate_10",str(rate_10)),("unique",str(unique_calls)),("countries",str(countries))]:
            if k in self._stat_widgets: self._stat_widgets[k].config(text=v)
        for w in self._band_frame.winfo_children(): w.destroy()
        band_counts=Counter(q.get("b","?") for q in log); total_q=max(1,len(log))
        active_bands=sorted([(b,band_counts[b]) for b in BANDS_ALL if band_counts.get(b,0)>0],key=lambda x:-x[1])
        for band,cnt in active_bands[:6]:
            bf=tk.Frame(self._band_frame,bg=TH["bg"]); bf.pack(fill="x",pady=1)
            tk.Label(bf,text=f"{band:<5}",bg=TH["bg"],fg=TH["fg"],font=("Consolas",8),width=5).pack(side="left")
            pct=cnt*100//total_q
            bar_frame=tk.Frame(bf,bg=TH["entry_bg"],height=12,width=200); bar_frame.pack(side="left",padx=4); bar_frame.pack_propagate(False)
            tk.Frame(bar_frame,bg=TH["accent"],height=12,width=max(2,pct*2)).pack(side="left")
            tk.Label(bf,text=f"{cnt}",bg=TH["bg"],fg=TH["gold"],font=("Consolas",8)).pack(side="left")
        self._upd_lbl.config(text=f"Actualizat: {now.strftime('%H:%M:%S')} UTC")

    def _schedule(self):
        try:
            if self.winfo_exists(): self._refresh(); self.after(15000,self._schedule)
        except: pass
