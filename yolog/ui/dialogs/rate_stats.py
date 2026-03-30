# -*- coding: utf-8 -*-
"""ui/dialogs/rate_stats.py — Statistici Rate QSO live"""
import datetime, tkinter as tk
from tkinter import ttk
from collections import Counter
from ..theme import TH
from ...core.dxcc import DXCC
from ...core.bands import BANDS_ALL

class RateStatsWindow(tk.Toplevel):
    def __init__(self, parent, log_getter, cfg_getter):
        super().__init__(parent)
        self.log_getter=log_getter; self.cfg_getter=cfg_getter
        self.title(" Statistici Rate QSO — YO Log PRO v19")
        try: sw,sh=self.winfo_screenwidth(),self.winfo_screenheight()
        except: sw,sh=1366,768
        self.geometry(f"{min(900,int(sw*.9))}x{min(600,int(sh*.88))}")
        self.configure(bg=TH["bg"]); self._build(); self._refresh(); self._schedule()

    def _build(self):
        hdr=tk.Frame(self,bg=TH["header_bg"],pady=4); hdr.pack(fill="x")
        tk.Label(hdr,text=" Statistici Rate QSO — Live",bg=TH["header_bg"],fg=TH["gold"],font=("Consolas",12,"bold")).pack(side="left",padx=10)
        tk.Button(hdr,text="R Refresh",command=self._refresh,bg=TH["accent"],fg="white",font=("Consolas",10)).pack(side="right",padx=6)
        mf=tk.Frame(self,bg=TH["bg"]); mf.pack(fill="both",expand=True,padx=6,pady=4)
        lf=tk.Frame(mf,bg=TH["bg"]); lf.pack(side="left",fill="both",expand=True)
        tk.Label(lf,text="QSO / oră",bg=TH["bg"],fg=TH["fg"],font=("Consolas",10,"bold")).pack(anchor="w")
        self._rate_canvas=tk.Canvas(lf,bg=TH["bg"],highlightthickness=1,highlightbackground=TH["accent"],width=480,height=260)
        self._rate_canvas.pack(fill="both",expand=True,pady=4)
        rf=tk.Frame(mf,bg=TH["bg"],width=320); rf.pack(side="right",fill="y",padx=(6,0)); rf.pack_propagate(False)
        tk.Label(rf,text="Top DXCC",bg=TH["bg"],fg=TH["gold"],font=("Consolas",10,"bold")).pack(anchor="w",pady=(0,2))
        dxcc_f=tk.Frame(rf,bg=TH["bg"]); dxcc_f.pack(fill="x")
        self._dxcc_tree=ttk.Treeview(dxcc_f,columns=("dxcc","count"),show="headings",height=8)
        self._dxcc_tree.heading("dxcc",text="DXCC/Țară"); self._dxcc_tree.heading("count",text="QSO")
        self._dxcc_tree.column("dxcc",width=200); self._dxcc_tree.column("count",width=60,anchor="center")
        dxcc_sb=ttk.Scrollbar(dxcc_f,orient="vertical",command=self._dxcc_tree.yview); self._dxcc_tree.configure(yscrollcommand=dxcc_sb.set)
        dxcc_sb.pack(side="right",fill="y"); self._dxcc_tree.pack(side="left",fill="x",expand=True)
        tk.Label(rf,text="Per Bandă",bg=TH["bg"],fg=TH["gold"],font=("Consolas",10,"bold")).pack(anchor="w",pady=(8,2))
        band_f=tk.Frame(rf,bg=TH["bg"]); band_f.pack(fill="x")
        self._band_tree=ttk.Treeview(band_f,columns=("band","count","pct"),show="headings",height=8)
        for col,hdr,w,anch in [("band","Bandă",70,"center"),("count","QSO",60,"center"),("pct","%",50,"center")]:
            self._band_tree.heading(col,text=hdr); self._band_tree.column(col,width=w,anchor=anch)
        band_sb=ttk.Scrollbar(band_f,orient="vertical",command=self._band_tree.yview); self._band_tree.configure(yscrollcommand=band_sb.set)
        band_sb.pack(side="right",fill="y"); self._band_tree.pack(side="left",fill="x",expand=True)
        sf=tk.Frame(self,bg=TH["bg"]); sf.pack(fill="x",padx=6,pady=4)
        self._stat_labels={}
        for i,(k,lbl) in enumerate([("total","Total QSO"),("unique_calls","Indicative unice"),("dxcc_count","DXCC lucrate"),("rate_1h","Rate 1h"),("rate_last_qso","Ultimul QSO"),("top_band","Banda activă")]):
            r,c=divmod(i,3)
            frm=tk.Frame(sf,bg=TH["bg"],bd=1,relief="solid",padx=8,pady=4); frm.grid(row=r,column=c,padx=4,pady=2,sticky="ew"); sf.columnconfigure(c,weight=1)
            tk.Label(frm,text=lbl,bg=TH["bg"],fg=TH["fg"],font=("Consolas",8)).pack(anchor="w")
            val_lbl=tk.Label(frm,text="—",bg=TH["bg"],fg=TH["gold"],font=("Consolas",11,"bold")); val_lbl.pack(anchor="w"); self._stat_labels[k]=val_lbl

    def _refresh(self):
        log=self.log_getter()
        if not log: return
        hour_counts=Counter()
        for q in log:
            try:
                dt=datetime.datetime.strptime((q.get("d","")+" "+q.get("t","00:00")).strip(),"%Y-%m-%d %H:%M")
                hour_counts[dt.strftime("%Y-%m-%d %H")]+=1
            except: pass
        self._draw_chart(hour_counts)
        dxcc_counts=Counter(DXCC.lookup(q.get("c",""))[0] for q in log)
        for row in self._dxcc_tree.get_children(): self._dxcc_tree.delete(row)
        for country,cnt in dxcc_counts.most_common(20): self._dxcc_tree.insert("","end",values=(country,cnt))
        band_counts=Counter(q.get("b","?") for q in log); total=max(1,len(log))
        for row in self._band_tree.get_children(): self._band_tree.delete(row)
        for band in BANDS_ALL:
            cnt=band_counts.get(band,0)
            if cnt: self._band_tree.insert("","end",values=(band,cnt,f"{100*cnt//total}%"))
        unique_calls=len(set(q.get("c","") for q in log))
        dxcc_count=len(set(DXCC.lookup(q.get("c",""))[1] for q in log))
        top_band=band_counts.most_common(1)[0][0] if band_counts else "—"
        now=datetime.datetime.utcnow()
        rate_1h=sum(1 for q in log if self._in_win(q,now,60)); rate_last_qso="—"
        if len(log)>=2:
            try:
                def pdt(q): return datetime.datetime.strptime((q.get("d","")+" "+q.get("t","00:00")).strip(),"%Y-%m-%d %H:%M")
                sl=sorted(log,key=pdt); gap=pdt(sl[-1])-pdt(sl[-2]); rate_last_qso=f"{int(gap.total_seconds()//60)}m"
            except: pass
        for k,v in [("total",str(len(log))),("unique_calls",str(unique_calls)),("dxcc_count",str(dxcc_count)),("rate_1h",f"{rate_1h} QSO/h"),("rate_last_qso",rate_last_qso),("top_band",top_band)]:
            if k in self._stat_labels: self._stat_labels[k].config(text=v)

    def _in_win(self,q,now,minutes):
        try:
            dt=datetime.datetime.strptime((q.get("d","")+" "+q.get("t","00:00")).strip(),"%Y-%m-%d %H:%M")
            return (now-dt).total_seconds()<=minutes*60
        except: return False

    def _draw_chart(self,hour_counts):
        c=self._rate_canvas; c.delete("all")
        cw=c.winfo_width() or 480; ch=c.winfo_height() or 260
        pad_l,pad_r,pad_t,pad_b=40,10,10,30
        if not hour_counts: c.create_text(cw//2,ch//2,text="Nu există date",fill=TH["fg"],font=("Consolas",11)); return
        sorted_hours=sorted(hour_counts.keys())[-24:]; max_val=max(hour_counts[h] for h in sorted_hours) or 1; n=len(sorted_hours)
        if n==0: return
        bar_w=max(4,(cw-pad_l-pad_r)//n-2)
        for i in range(5):
            y=pad_t+(ch-pad_t-pad_b)*i//4; val=max_val*(4-i)//4
            c.create_line(pad_l,y,cw-pad_r,y,fill=TH["accent"],dash=(2,4))
            c.create_text(pad_l-4,y,text=str(val),fill=TH["fg"],font=("Consolas",7),anchor="e")
        max_h=max(hour_counts[h] for h in sorted_hours)
        for i,hour in enumerate(sorted_hours):
            x=pad_l+i*(bar_w+2); val=hour_counts[hour]; bar_h=int((ch-pad_t-pad_b)*val/max_val)
            y0=ch-pad_b-bar_h; col=TH.get("cyan","#00aaff") if val==max_h else TH["accent"]
            c.create_rectangle(x,y0,x+bar_w,ch-pad_b,fill=col,outline="")
            c.create_text(x+bar_w//2,y0-8,text=str(val),fill=TH["fg"],font=("Consolas",7))
            c.create_text(x+bar_w//2,ch-pad_b+12,text=hour[-2:]+"h",fill=TH["fg"],font=("Consolas",7))

    def _schedule(self):
        try:
            if self.winfo_exists(): self._refresh(); self.after(60000,self._schedule)
        except: pass
