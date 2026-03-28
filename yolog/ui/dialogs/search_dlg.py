# -*- coding: utf-8 -*-
"""ui/dialogs/search_dlg.py"""
import tkinter as tk
from tkinter import ttk
from ..theme import TH
from ... import i18n

class SearchDialog(tk.Toplevel):
    def __init__(self, parent, log_data):
        super().__init__(parent)
        self._log=log_data; self.title(i18n.t("search_t"))
        try: sw,sh=self.winfo_screenwidth(),self.winfo_screenheight()
        except: sw,sh=1366,768
        w,h=min(700,int(sw*.9)),min(500,int(sh*.85))
        self.geometry(f"{w}x{h}"); self.configure(bg=TH["bg"]); self.transient(parent)
        fn=("Consolas",11)
        sf=tk.Frame(self,bg=TH["bg"]); sf.pack(fill="x",padx=10,pady=8)
        tk.Label(sf,text=i18n.t("search_l"),bg=TH["bg"],fg=TH["fg"],font=fn).pack(side="left")
        self._sv=tk.StringVar()
        e=tk.Entry(sf,textvariable=self._sv,width=30,bg=TH["entry_bg"],fg=TH["fg"],font=fn,insertbackground=TH["fg"])
        e.pack(side="left",padx=6); e.bind("<KeyRelease>",self._search); e.focus_set()
        cols=["call","band","mode","date","time","note","freq"]
        self._tree=ttk.Treeview(self,columns=cols,show="headings")
        for c,w2 in zip(cols,[120,60,60,90,60,120,80]):
            self._tree.heading(c,text=c.upper()); self._tree.column(c,width=w2,anchor="center")
        sb=ttk.Scrollbar(self,orient="vertical",command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side="left",fill="both",expand=True,padx=(10,0),pady=4)
        sb.pack(side="right",fill="y",padx=(0,10),pady=4)
        tk.Button(self,text=i18n.t("close"),command=self.destroy,bg=TH["btn_bg"],fg="white",font=fn).pack(pady=6)
        self._search()

    def _search(self,e=None):
        q=self._sv.get().upper().strip()
        for i in self._tree.get_children(): self._tree.delete(i)
        for qso in self._log:
            if not q or q in qso.get("c","").upper() or q in qso.get("n","").upper():
                self._tree.insert("","end",values=[qso.get("c",""),qso.get("b",""),qso.get("m",""),qso.get("d",""),qso.get("t",""),qso.get("n",""),qso.get("f","")])
