# -*- coding: utf-8 -*-
"""ui/dialogs/cabrillo_dlg.py — Dialoguri configurare export Cabrillo 3.0 și 2.0"""
import tkinter as tk
from tkinter import ttk
from ..theme import TH
from ... import i18n
from ...core.bands import BANDS_ALL

def _rg(d,p,iw,ih):
    try: sw,sh=d.winfo_screenwidth(),d.winfo_screenheight()
    except: sw,sh=1366,768
    w,h=min(iw,int(sw*.92)),min(ih,int(sh*.88))
    try: x=p.winfo_rootx()+(p.winfo_width()-w)//2; y=p.winfo_rooty()+(p.winfo_height()-h)//2
    except: x,y=(sw-w)//2,(sh-h)//2
    d.geometry(f"{w}x{h}+{max(0,x)}+{max(0,y)}")

EXCH_SENT_OPTIONS = {
    "ro": {"county":"Județ ({jud})","grid":"Locator ({loc})","serial":"Nr. Serial","none":"Nimic (--)"},
    "en": {"county":"County ({jud})","grid":"Locator ({loc})","serial":"Serial Nr.","none":"None (--)"},
}
EXCH_RCVD_OPTIONS = {
    "ro": {"log":"Din log (notă/serial)","none":"Nimic (--)"},
    "en": {"log":"From log (note/serial)","none":"None (--)"},
}

class Cab3ConfigDialog(tk.Toplevel):
    """Dialog configurare export Cabrillo 3.0."""
    def __init__(self, parent, cfg):
        super().__init__(parent)
        self.result=None; self.cfg=cfg
        self.title("Configurare Cabrillo 3.0"); _rg(self,parent,460,340)
        self.configure(bg=TH["bg"]); self.transient(parent); self.grab_set()
        lo={"bg":TH["bg"],"fg":TH["fg"],"font":("Consolas",11)}
        lang = i18n.get_lang()

        tk.Label(self,text="Format dată QSO:" if lang=="ro" else "QSO Date Format:",**lo).pack(anchor="w",padx=15,pady=(15,0))
        self._date_opts=["YYYYMMDD (standard Cabrillo 3.0)","YYYY-MM-DD (cu liniuțe)"] if lang=="ro" else ["YYYYMMDD (Cabrillo 3.0 standard)","YYYY-MM-DD (with dashes)"]
        saved_fmt=cfg.get("cab3_date_fmt","no_dash")
        self._date_v=tk.StringVar(value=self._date_opts[0] if saved_fmt!="with_dash" else self._date_opts[1])
        ttk.Combobox(self,textvariable=self._date_v,values=self._date_opts,state="readonly",width=34,font=("Consolas",11)).pack(padx=15,pady=4)

        tk.Label(self,text="Tip operator:" if lang=="ro" else "Operator type:",**lo).pack(anchor="w",padx=15,pady=(10,0))
        self._op_opts=["SINGLE-OP","MULTI-OP","CHECKLOG"]
        saved_op=cfg.get("cab3_operator","SINGLE-OP")
        self._op_v=tk.StringVar(value=saved_op if saved_op in self._op_opts else "SINGLE-OP")
        ttk.Combobox(self,textvariable=self._op_v,values=self._op_opts,state="readonly",width=34,font=("Consolas",11)).pack(padx=15,pady=4)

        tk.Label(self,text="Categorie putere:" if lang=="ro" else "Power category:",**lo).pack(anchor="w",padx=15,pady=(10,0))
        self._pwr_opts=["HIGH","LOW","QRP"]
        try: pw=int(cfg.get("power","100"))
        except: pw=100
        auto_pwr="QRP" if pw<=5 else ("LOW" if pw<=100 else "HIGH")
        saved_pwr=cfg.get("cab3_power",auto_pwr)
        self._pwr_v=tk.StringVar(value=saved_pwr if saved_pwr in self._pwr_opts else auto_pwr)
        ttk.Combobox(self,textvariable=self._pwr_v,values=self._pwr_opts,state="readonly",width=34,font=("Consolas",11)).pack(padx=15,pady=4)

        bf=tk.Frame(self,bg=TH["bg"]); bf.pack(pady=14)
        tk.Button(bf,text=" Exportă",command=self._ok,bg=TH["ok"],fg="white",font=("Consolas",12,"bold")).pack(side="left",padx=8)
        tk.Button(bf,text=i18n.t("cancel"),command=self.destroy,bg=TH["btn_bg"],fg="white",font=("Consolas",12)).pack(side="left",padx=8)

    def _ok(self):
        date_fmt="with_dash" if self._date_v.get()==self._date_opts[1] else "no_dash"
        self.result={"date_fmt":date_fmt,"operator":self._op_v.get(),"power":self._pwr_v.get()}
        self.destroy()


class Cab2ConfigDialog(tk.Toplevel):
    """Dialog configurare export Cabrillo 2.0."""
    def __init__(self, parent, cfg):
        super().__init__(parent)
        self.result=None; self.cfg=cfg
        self.title(i18n.t("cab2_config")); _rg(self,parent,440,310)
        self.configure(bg=TH["bg"]); self.transient(parent); self.grab_set()
        lo={"bg":TH["bg"],"fg":TH["fg"],"font":("Consolas",11)}
        lang=i18n.get_lang(); jud=cfg.get("county",cfg.get("jud","NT")); loc=cfg.get("loc","KN37")

        # Exchange trimis
        tk.Label(self,text="Exchange TRIMIS:" if lang=="ro" else "Exchange SENT:",**lo).pack(anchor="w",padx=15,pady=(15,0))
        sent_opts=EXCH_SENT_OPTIONS.get(lang,EXCH_SENT_OPTIONS["ro"])
        self._sent_labels={}; self._sent_values=[]
        for k,lbl in sent_opts.items():
            display=lbl.format(jud=jud,loc=loc); self._sent_labels[display]=k; self._sent_values.append(display)
        saved=cfg.get("cab2_exch_sent","none"); default_sent=self._sent_values[-1]
        for d,k in self._sent_labels.items():
            if k==saved: default_sent=d; break
        self._sent_v=tk.StringVar(value=default_sent)
        ttk.Combobox(self,textvariable=self._sent_v,values=self._sent_values,state="readonly",width=30,font=("Consolas",11)).pack(padx=15,pady=4)

        # Exchange primit
        tk.Label(self,text="Exchange PRIMIT:" if lang=="ro" else "Exchange RECEIVED:",**lo).pack(anchor="w",padx=15,pady=(8,0))
        rcvd_opts=EXCH_RCVD_OPTIONS.get(lang,EXCH_RCVD_OPTIONS["ro"])
        self._rcvd_labels={}; self._rcvd_values=[]
        for k,lbl in rcvd_opts.items(): self._rcvd_labels[lbl]=k; self._rcvd_values.append(lbl)
        saved_r=cfg.get("cab2_exch_rcvd","log"); default_rcvd=self._rcvd_values[0]
        for d,k in self._rcvd_labels.items():
            if k==saved_r: default_rcvd=d; break
        self._rcvd_v=tk.StringVar(value=default_rcvd)
        ttk.Combobox(self,textvariable=self._rcvd_v,values=self._rcvd_values,state="readonly",width=30,font=("Consolas",11)).pack(padx=15,pady=4)

        # Format dată
        date_label="Format dată QSO:" if lang=="ro" else "QSO Date Format:"
        tk.Label(self,text=date_label,**lo).pack(anchor="w",padx=15,pady=(8,0))
        self._date_opts=["YYYY-MM-DD (standard Cabrillo)","YYYYMMDD (fără liniuțe)"] if lang=="ro" else ["YYYY-MM-DD (Cabrillo standard)","YYYYMMDD (no dashes)"]
        saved_fmt=cfg.get("cab2_date_fmt","with_dash")
        self._date_v=tk.StringVar(value=self._date_opts[0] if saved_fmt!="no_dash" else self._date_opts[1])
        ttk.Combobox(self,textvariable=self._date_v,values=self._date_opts,state="readonly",width=34,font=("Consolas",11)).pack(padx=15,pady=4)

        bf=tk.Frame(self,bg=TH["bg"]); bf.pack(pady=14)
        tk.Button(bf,text=i18n.t("cab2_export"),command=self._ok,bg=TH["ok"],fg="white",font=("Consolas",12,"bold")).pack(side="left",padx=8)
        tk.Button(bf,text=i18n.t("cancel"),command=self.destroy,bg=TH["btn_bg"],fg="white",font=("Consolas",12)).pack(side="left",padx=8)

    def _ok(self):
        date_fmt="no_dash" if self._date_v.get()==self._date_opts[1] else "with_dash"
        self.result={"sent":self._sent_labels.get(self._sent_v.get(),"none"),"rcvd":self._rcvd_labels.get(self._rcvd_v.get(),"log"),"date_fmt":date_fmt}
        self.destroy()
