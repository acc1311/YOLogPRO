# -*- coding: utf-8 -*-
"""ui/dialogs/band_map.py — Band Map Window"""
import datetime, tkinter as tk
from tkinter import ttk
from ..theme import TH
from ...core.dxcc import DXCC
from ...core.locator import Loc
from ...core.bands import BANDS_ALL

BAND_COLORS = {
    "160m":"#ff4444","80m":"#ff8800","60m":"#ffcc00","40m":"#88ff00","30m":"#00ff88",
    "20m":"#00aaff","17m":"#4488ff","15m":"#8844ff","12m":"#ff44aa","10m":"#ff0066",
    "6m":"#00ffff","2m":"#44ffaa","70cm":"#aaffee","23cm":"#ffffff"
}

class BandMapWindow(tk.Toplevel):
    def __init__(self, parent, log_getter, cfg_getter):
        super().__init__(parent)
        self.log_getter=log_getter; self.cfg_getter=cfg_getter
        self.title(" Band Map — YO Log PRO v19")
        try: sw,sh=self.winfo_screenwidth(),self.winfo_screenheight()
        except: sw,sh=1366,768
        self.geometry(f"{min(860,int(sw*.9))}x{min(520,int(sh*.85))}")
        self.configure(bg=TH["bg"]); self.resizable(True,True)
        self._build(); self._refresh(); self._schedule()

    def _build(self):
        hdr=tk.Frame(self,bg=TH["header_bg"],pady=4); hdr.pack(fill="x")
        tk.Label(hdr,text=" Band Map — Activitate în timp real",bg=TH["header_bg"],
                 fg=TH["gold"],font=("Consolas",12,"bold")).pack(side="left",padx=10)
        tk.Button(hdr,text="R Refresh",command=self._refresh,
                  bg=TH["accent"],fg="white",font=("Consolas",10)).pack(side="right",padx=6)
        self._canvas=tk.Canvas(self,bg=TH["bg"],highlightthickness=0)
        vsb=ttk.Scrollbar(self,orient="vertical",command=self._canvas.yview)
        hsb=ttk.Scrollbar(self,orient="horizontal",command=self._canvas.xview)
        self._canvas.configure(yscrollcommand=vsb.set,xscrollcommand=hsb.set)
        vsb.pack(side="right",fill="y"); hsb.pack(side="bottom",fill="x")
        self._canvas.pack(fill="both",expand=True,padx=4,pady=4)
        self._canvas.bind("<MouseWheel>",lambda e:self._canvas.yview_scroll(int(-1*(e.delta/120)),"units"))
        self._stat_lbl=tk.Label(self,text="",bg=TH["bg"],fg=TH["fg"],font=("Consolas",9))
        self._stat_lbl.pack(side="bottom",fill="x",padx=6,pady=2)

    def _refresh(self):
        self._canvas.delete("all")
        log=self.log_getter(); cfg=self.cfg_getter(); my_loc=cfg.get("loc","")
        band_qsos={}
        for q in log:
            b=q.get("b","?")
            band_qsos.setdefault(b,[]).append(q)
        cw=max(60,self._canvas.winfo_width() or 820)
        col_w=max(50,(cw-20)//len(BANDS_ALL)); row_h=22
        max_rows=max((len(v) for v in band_qsos.values()),default=0)
        canvas_h=max(300,(max_rows+3)*row_h+60)
        self._canvas.configure(scrollregion=(0,0,cw,canvas_h))
        my_country,_=DXCC.lookup(cfg.get("call","YO8ACR"))
        for ci,band in enumerate(BANDS_ALL):
            x=10+ci*col_w; color=BAND_COLORS.get(band,"#888888"); count=len(band_qsos.get(band,[]))
            self._canvas.create_rectangle(x,5,x+col_w-2,30,fill=color,outline="")
            self._canvas.create_text(x+col_w//2,17,text=band,font=("Consolas",9,"bold"),fill="#000000")
            self._canvas.create_text(x+col_w//2,42,text=f"{count} QSO",font=("Consolas",8),fill=color)
            for ri,q in enumerate(reversed(band_qsos.get(band,[])[-20:])):
                y=55+ri*row_h; call=q.get("c","?"); country,_=DXCC.lookup(call)
                is_dx=country!=my_country and country!="Unknown"
                row_color=TH.get("cyan","#00aaff") if is_dx else TH["fg"]
                note=q.get("n",""); freq=q.get("f","")
                disp=f"{call[:9]}"; 
                if freq: disp+=f" {freq}k"
                self._canvas.create_text(x+3,y+11,text=disp,font=("Consolas",8),fill=row_color,anchor="w")
        total=len(log); dxcc_set=set(DXCC.prefix(q.get("c","")) for q in log)
        self._stat_lbl.config(text=f"Total QSO: {total}  |  DXCC: {len(dxcc_set)}  |  Benzi active: {len(band_qsos)}  |  {datetime.datetime.utcnow().strftime('%H:%M:%S')} UTC")

    def _schedule(self):
        try:
            if self.winfo_exists(): self._refresh(); self.after(30000,self._schedule)
        except: pass
