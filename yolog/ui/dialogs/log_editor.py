# -*- coding: utf-8 -*-
"""ui/dialogs/log_editor.py — Log Editor dedicat (port fidel din v17.1)"""
import copy, datetime, tkinter as tk
from tkinter import ttk, messagebox
from collections import deque
from ..theme import TH
from ... import i18n
from ...core.score import Score
from ...core.dxcc import DXCC
from ...core.bands import BANDS_ALL, MODES_ALL
from .calendar_popup import CalendarPopup

def _normalize_time(raw):
    if not raw: return "00:00"
    t=raw.strip().replace(":","").replace(".","")
    if not t.isdigit(): return raw.strip()
    if len(t)<=2: return f"00:{int(t):02d}"
    if len(t)==3: return f"{int(t[0]):02d}:{t[1:]}"
    if len(t)>=4: return f"{t[:2]}:{t[2:4]}"
    return raw.strip()

class LogEditorWindow(tk.Toplevel):
    def __init__(self, parent, log_ref, contests_ref, cfg_ref, on_change=None, cid_getter=None):
        super().__init__(parent)
        self._log=log_ref; self._contests=contests_ref; self._cfg=cfg_ref
        self._on_change=on_change; self._cid_getter=cid_getter
        self._edit_idx=None; self._sort_col=None; self._sort_rev=False
        self._undo_stack=deque(maxlen=50)
        self.title(" Log Editor — YO Log PRO v19")
        try: sw,sh=self.winfo_screenwidth(),self.winfo_screenheight()
        except: sw,sh=1366,768
        self.geometry(f"{min(1200,int(sw*.95))}x{min(700,int(sh*.90))}")
        self.configure(bg=TH["bg"]); self.resizable(True,True)
        self._build(); self._refresh()
        self.after(150,self._focus_call_field)

    def _build(self):
        # Toolbar
        tb=tk.Frame(self,bg=TH["header_bg"],pady=5); tb.pack(fill="x")
        tk.Label(tb,text=" Log Editor",bg=TH["header_bg"],fg=TH["gold"],
                 font=("Consolas",12,"bold")).pack(side="left",padx=10)
        self._save_btn=tk.Button(tb,text=" Salvează",command=self._save_entry,
                                  bg=TH["ok"],fg="white",font=("Consolas",10,"bold"))
        self._save_btn.pack(side="left",padx=2)
        for lbl,cmd,col,w in [(" Șterge",self._delete_sel,TH["err"],10),
                                ("<- Undo",self._undo,TH["warn"],8),
                                (" Căutare",self._do_search,TH["accent"],10),
                                ("R Refresh",self._refresh,TH["btn_bg"],9)]:
            tk.Button(tb,text=lbl,command=cmd,bg=col,fg="white",font=("Consolas",10),width=w).pack(side="left",padx=2)
        self._status=tk.Label(tb,text="",bg=TH["header_bg"],fg=TH["fg"],font=("Consolas",9))
        self._status.pack(side="right",padx=8)

        # Filtru rapid
        sf=tk.Frame(self,bg=TH["bg"],pady=3); sf.pack(fill="x",padx=8)
        tk.Label(sf,text=" Filtru rapid:",bg=TH["bg"],fg=TH["fg"],font=("Consolas",9)).pack(side="left")
        self._search_v=tk.StringVar()
        se=tk.Entry(sf,textvariable=self._search_v,width=20,bg=TH["entry_bg"],fg=TH["gold"],
                    font=("Consolas",10),insertbackground=TH["fg"])
        se.pack(side="left",padx=4); se.bind("<KeyRelease>",lambda e:self._refresh())
        tk.Label(sf,text="Bandă:",bg=TH["bg"],fg=TH["fg"],font=("Consolas",9)).pack(side="left",padx=(8,0))
        self._fband_v=tk.StringVar(value="Toate")
        bb=ttk.Combobox(sf,textvariable=self._fband_v,values=["Toate"]+BANDS_ALL,state="readonly",width=7)
        bb.pack(side="left",padx=4); bb.bind("<<ComboboxSelected>>",lambda e:self._refresh())
        tk.Label(sf,text="Mod:",bg=TH["bg"],fg=TH["fg"],font=("Consolas",9)).pack(side="left")
        self._fmode_v=tk.StringVar(value="Toate")
        mb=ttk.Combobox(sf,textvariable=self._fmode_v,values=["Toate"]+MODES_ALL,state="readonly",width=7)
        mb.pack(side="left",padx=4); mb.bind("<<ComboboxSelected>>",lambda e:self._refresh())
        self._count_lbl=tk.Label(sf,text="",bg=TH["bg"],fg=TH["gold"],font=("Consolas",9,"bold"))
        self._count_lbl.pack(side="right",padx=8)

        # Treeview
        tf=tk.Frame(self,bg=TH["bg"]); tf.pack(fill="both",expand=True,padx=8,pady=(0,4))
        cols=("nr","call","freq","band","mode","rst_s","rst_r","ss","sr","note","country","date","time","pts")
        hdrs=["Nr","Indicativ","Freq","Bandă","Mod","RST S","RST R","Nr S","Nr R","Notă","Țara","Dată","Oră","Pt"]
        wids=[38,110,75,55,55,48,48,45,45,95,95,88,50,45]
        self._tree=ttk.Treeview(tf,columns=cols,show="headings",selectmode="extended")
        for c,h,w in zip(cols,hdrs,wids):
            self._tree.heading(c,text=h,command=lambda col=c:self._sort(col))
            self._tree.column(c,width=w,anchor="center")
        vsb=ttk.Scrollbar(tf,orient="vertical",command=self._tree.yview)
        hsb=ttk.Scrollbar(tf,orient="horizontal",command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set,xscrollcommand=hsb.set)
        self._tree.grid(row=0,column=0,sticky="nsew"); vsb.grid(row=0,column=1,sticky="ns"); hsb.grid(row=1,column=0,sticky="ew")
        tf.rowconfigure(0,weight=1); tf.columnconfigure(0,weight=1)
        self._tree.tag_configure("dup",background=TH["dup_bg"]); self._tree.tag_configure("alt",background=TH["alt"]); self._tree.tag_configure("spec",background=TH["spec_bg"])
        self._tree.bind("<Double-1>",lambda e:self._load_into_form())
        self._tree.bind("<Delete>",lambda e:self._delete_sel())
        self._tree.bind("<Button-3>",self._ctx_menu)
        self._tree.bind("<MouseWheel>",lambda e:self._tree.yview_scroll(int(-1*(e.delta/120)),"units"))
        self._tree.bind("<Button-4>",lambda e:self._tree.yview_scroll(-1,"units"))
        self._tree.bind("<Button-5>",lambda e:self._tree.yview_scroll(1,"units"))

        # Edit Form
        ef=tk.LabelFrame(self,text="  Editare QSO — dublu-click pe rând, modifică câmpurile și apasă Salvează ",
                          bg=TH["bg"],fg=TH["gold"],font=("Consolas",9,"bold"),pady=6,padx=10)
        ef.pack(fill="x",padx=8,pady=(0,6))
        EO=dict(bg=TH["entry_bg"],fg=TH["gold"],font=("Consolas",11),insertbackground="white",relief="solid",bd=1,justify="center")
        LO=dict(bg=TH["bg"],fg="#aaaaaa",font=("Consolas",8))
        self._ent={}

        def _lbl_ent(parent,label,key,width,is_combo=False,combo_vals=None):
            frm=tk.Frame(parent,bg=TH["bg"]); frm.pack(side="left",padx=4)
            tk.Label(frm,text=label,**LO).pack(anchor="w")
            if is_combo:
                v=tk.StringVar()
                w=ttk.Combobox(frm,textvariable=v,values=combo_vals or [],state="normal",width=width,font=("Consolas",11))
                w.pack(); self._ent[key]=v; return v,w
            else:
                e=tk.Entry(frm,width=width,**EO); e.pack(); self._ent[key]=e; return e,e

        r1=tk.Frame(ef,bg=TH["bg"]); r1.pack(fill="x",pady=(4,2))
        ce,_=_lbl_ent(r1,"Indicativ","call",12); ce.bind("<KeyRelease>",self._on_call_key)
        _lbl_ent(r1,"Freq (kHz)","freq",9)
        _lbl_ent(r1,"Bandă","band",7,is_combo=True,combo_vals=BANDS_ALL)
        _lbl_ent(r1,"Mod","mode",7,is_combo=True,combo_vals=MODES_ALL)
        _lbl_ent(r1,"RST S","rst_s",5); _lbl_ent(r1,"RST R","rst_r",5)
        bf_r=tk.Frame(r1,bg=TH["bg"]); bf_r.pack(side="right",padx=8)
        self._save_btn2=tk.Button(bf_r,text=" Salvează",command=self._save_entry,
                                   bg=TH["ok"],fg="white",font=("Consolas",10,"bold"))
        self._save_btn2.pack(pady=1)
        tk.Button(bf_r,text=" Anulează",command=self._cancel_edit,
                  bg=TH["btn_bg"],fg="white",font=("Consolas",9)).pack(pady=1)

        r2=tk.Frame(ef,bg=TH["bg"]); r2.pack(fill="x",pady=(2,4))
        _lbl_ent(r2,"Nr Serial S","ss",7); _lbl_ent(r2,"Nr Serial R","sr",7)
        _lbl_ent(r2,"Notă / Locator","note",22)
        _lbl_ent(r2,"Data","date",12)
        _cal_frm=tk.Frame(r2,bg=TH["bg"]); _cal_frm.pack(side="left",padx=0)
        tk.Label(_cal_frm,text=" ",bg=TH["bg"],fg=TH["bg"],font=("Consolas",8)).pack()
        tk.Button(_cal_frm,text="",command=self._open_cal,bg="#1a5276",fg="white",font=("Consolas",9)).pack()
        _lbl_ent(r2,"Ora (HH:MM)","time",8)
        if "time" in self._ent:
            self._ent["time"].bind("<FocusOut>",lambda e:self._norm_time())
            self._ent["time"].bind("<Return>",lambda e:self._norm_time())

    def _open_cal(self):
        if "date" not in self._ent: return
        def _set(ds): self._ent["date"].delete(0,"end"); self._ent["date"].insert(0,ds)
        CalendarPopup(self._ent["date"], self._ent["date"].get().strip(), _set)

    def _norm_time(self):
        if "time" not in self._ent: return
        raw=self._ent["time"].get().strip(); norm=_normalize_time(raw)
        if norm!=raw: self._ent["time"].delete(0,"end"); self._ent["time"].insert(0,norm)

    def _ctx_menu(self,event):
        item=self._tree.identify_row(event.y)
        if item: self._tree.selection_set(item)
        ctx=tk.Menu(self,tearoff=0)
        ctx.add_command(label=" Editează",command=self._load_into_form)
        ctx.add_command(label=" Șterge",command=self._delete_sel)
        ctx.add_separator()
        ctx.add_command(label=" Copiază call",command=self._copy_call)
        ctx.post(event.x_root,event.y_root)

    def _sel_call(self):
        sel=self._tree.selection()
        if not sel: return ""
        try: return self._log[int(sel[0])].get("c","")
        except: return ""

    def _copy_call(self):
        call=self._sel_call()
        if call:
            try: self.clipboard_clear(); self.clipboard_append(call)
            except: pass

    def _refresh(self):
        for row in self._tree.get_children(): self._tree.delete(row)
        fq=self._search_v.get().upper().strip()
        fb=self._fband_v.get(); fm=self._fmode_v.get()
        cc=self._cc(); hs=cc.get("scoring_mode","none")!="none"
        sp=set((cc.get("special_scoring") or {}).keys()); seen=set(); shown=0
        for i,q in enumerate(self._log):
            b,m,c=q.get("b",""),q.get("m",""),q.get("c","").upper()
            if fb!="Toate" and b!=fb: continue
            if fm!="Toate" and m!=fm: continue
            if fq and fq not in c and fq not in q.get("n","").upper(): continue
            nr=len(self._log)-i; key=(c,b,m)
            tag=("dup",) if key in seen else ("spec",) if c in sp else ("alt",) if i%2==0 else ()
            seen.add(key); country,_=DXCC.lookup(c); pts=Score.qso(q,cc,self._cfg) if hs else ""
            self._tree.insert("","end",iid=str(i),values=(nr,c,q.get("f",""),b,m,q.get("s","59"),q.get("r","59"),q.get("ss",""),q.get("sr",""),q.get("n",""),country if country!="Unknown" else "",q.get("d",""),q.get("t",""),pts),tags=tag)
            shown+=1
        self._count_lbl.config(text=f"Afișat: {shown}/{len(self._log)} QSO")
        self._set_status(f"Log: {len(self._log)} QSO total")

    def _sort(self,col):
        if self._sort_col==col: self._sort_rev=not self._sort_rev
        else: self._sort_col=col; self._sort_rev=False
        items=[(self._tree.set(k,col),k) for k in self._tree.get_children("")]
        try: items.sort(key=lambda x:float(x[0]) if x[0].lstrip("-").replace(".","").isdigit() else x[0],reverse=self._sort_rev)
        except: items.sort(key=lambda x:x[0],reverse=self._sort_rev)
        for idx,(_,k) in enumerate(items): self._tree.move(k,"",idx)

    def _load_into_form(self):
        sel=self._tree.selection()
        if not sel: return
        try: idx=int(sel[0])
        except: return
        if idx<0 or idx>=len(self._log): return
        self._edit_idx=idx; q=self._log[idx]
        def _set(key,val):
            w=self._ent.get(key)
            if w is None: return
            if isinstance(w,tk.StringVar): w.set(val)
            else: w.delete(0,"end"); w.insert(0,val)
        for k,fk in [("call","c"),("freq","f"),("band","b"),("mode","m"),("rst_s","s"),("rst_r","r"),("ss","ss"),("sr","sr"),("note","n"),("date","d"),("time","t")]:
            _set(k,q.get(fk,""))
        for btn in [self._save_btn,self._save_btn2]:
            if btn: btn.config(text=" Actualizează",bg=TH["warn"])
        self._set_status(f"Editezi QSO #{len(self._log)-idx}: {q.get('c','')}")

    def _get_form(self):
        def _g(key):
            w=self._ent.get(key)
            if w is None: return ""
            return w.get().strip() if not isinstance(w,tk.StringVar) else w.get()
        return {"c":_g("call").upper(),"f":_g("freq"),"b":_g("band"),"m":_g("mode"),
                "s":_g("rst_s") or "59","r":_g("rst_r") or "59",
                "ss":_g("ss"),"sr":_g("sr"),"n":_g("note"),
                "d":_g("date"),"t":_normalize_time(_g("time"))}

    def _focus_call_field(self):
        try:
            w=self._ent.get("call")
            if w and hasattr(w,"focus_set"): w.focus_set()
        except: pass

    def _cancel_edit(self):
        self._edit_idx=None
        for w in self._ent.values():
            try:
                if isinstance(w,tk.StringVar): w.set("")
                else: w.delete(0,"end")
            except: pass
        for btn in [self._save_btn,self._save_btn2]:
            if btn:
                try: btn.config(text=" Salvează",bg=TH["ok"])
                except: pass
        self.after(50,self._focus_call_field)

    def _save_entry(self):
        q=self._get_form()
        if not q["c"]: messagebox.showwarning("Log Editor","Indicativul este obligatoriu!"); return
        if not q["b"] or not q["m"]: messagebox.showwarning("Log Editor","Banda și modul sunt obligatorii!"); return
        if self._edit_idx is not None:
            self._undo_stack.append(("upd",self._edit_idx,copy.deepcopy(self._log[self._edit_idx])))
            self._log[self._edit_idx]=q; self._set_status(f" Actualizat: {q['c']}")
        else:
            self._undo_stack.append(("add",0,q)); self._log.insert(0,q)
            self._set_status(f" Adăugat: {q['c']} {q['b']} {q['m']}")
        self._edit_idx=None
        for btn in [self._save_btn,self._save_btn2]:
            if btn:
                try: btn.config(text=" Salvează",bg=TH["ok"])
                except: pass
        self._save_to_disk(); self._refresh()
        if self._on_change: self._on_change()

    def _delete_sel(self):
        sel=self._tree.selection()
        if not sel: return
        n=len(sel)
        if not messagebox.askyesno("Log Editor",f"Ștergeți {n} QSO selectat{'e' if n>1 else ''}?"): return
        for idx in sorted([int(x) for x in sel],reverse=True):
            if 0<=idx<len(self._log):
                self._undo_stack.append(("del",idx,copy.deepcopy(self._log[idx])))
                self._log.pop(idx)
        self._save_to_disk(); self._refresh()
        if self._on_change: self._on_change()
        self._set_status(f" Șters {n} QSO.")

    def _undo(self):
        if not self._undo_stack: messagebox.showinfo("Undo","Nimic de anulat."); return
        act,idx,q=self._undo_stack.pop()
        if act=="add" and 0<=idx<len(self._log): self._log.pop(idx); self._set_status("<- Undo: adăugare anulată")
        elif act=="del": self._log.insert(idx,q); self._set_status("<- Undo: ștergere anulată")
        elif act=="upd":
            if 0<=idx<len(self._log): self._log[idx]=q
            self._set_status("<- Undo: modificare anulată")
        self._save_to_disk(); self._refresh()
        if self._on_change: self._on_change()

    def _do_search(self): self._refresh()
    def _on_call_key(self,event=None):
        w=self._ent.get("call")
        if w is None: return
        c=w.get().upper(); w.delete(0,"end"); w.insert(0,c)

    def _save_to_disk(self):
        try:
            from ...data.manager import get_dm
            cid=self._cid_getter() if self._cid_getter else "simplu"
            dm=get_dm(); dm.save_log(cid,self._log); dm.backup(cid,self._log)
        except Exception as e:
            messagebox.showerror("Eroare salvare",str(e))

    def _cc(self):
        try: cid=self._cid_getter() if self._cid_getter else "simplu"; return self._contests.get(cid,{})
        except: return {}

    def _set_status(self,msg):
        try: self._status.config(text=msg)
        except: pass
