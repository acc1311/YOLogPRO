# -*- coding: utf-8 -*-
"""
ui/dialogs/contest_mgr.py — Manager Concursuri + Editor complet
Permite: vizualizare, adaugare, editare, duplicare, stergere, import/export JSON
"""
from __future__ import annotations
import copy, json, os, tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from ..theme import TH
from ... import i18n
from ...core.bands import BANDS_ALL, MODES_ALL

COUNTIES = ["AB","AR","AG","BC","BH","BN","BT","BV","BR","BZ",
            "CS","CL","CJ","CT","CV","DB","DJ","GL","GR","GJ",
            "HR","HD","IL","IS","IF","MM","MH","MS","NT","OT",
            "PH","SM","SJ","SB","SV","TR","TM","TL","VS","VL","VN","B"]

def _rg(d, p, iw, ih):
    try: sw, sh = d.winfo_screenwidth(), d.winfo_screenheight()
    except: sw, sh = 1366, 768
    w, h = min(iw, int(sw*.92)), min(ih, int(sh*.88))
    try:
        d.update_idletasks()
        x = p.winfo_rootx()+(p.winfo_width()-w)//2
        y = p.winfo_rooty()+(p.winfo_height()-h)//2
        x = max(10, min(x, sw-w-10))
        y = max(10, min(y, sh-h-10))
    except: x, y = (sw-w)//2, (sh-h)//2
    d.geometry(f"{w}x{h}+{x}+{y}")


class ContestMgr(tk.Toplevel):
    """Manager principal: lista concursuri + butoane actiuni."""

    def __init__(self, parent, contests: dict):
        super().__init__(parent)
        self.result = None
        self._c = copy.deepcopy(contests)
        self.title("Manager Concursuri")
        _rg(self, parent, 960, 600)
        self.configure(bg=TH["bg"])
        self.transient(parent)
        self.grab_set()
        self._build()
        self._fill()

    def _build(self):
        fn = ("Consolas", 10)

        # Titlu
        tk.Label(self, text="Manager Concursuri YO Log PRO v19",
                 bg=TH["bg"], fg=TH["gold"],
                 font=("Consolas", 12, "bold")).pack(pady=(8,4))

        # Treeview cu lista concursuri
        tf = tk.Frame(self, bg=TH["bg"])
        tf.pack(fill="both", expand=True, padx=10, pady=4)

        cols = ("id", "name", "type", "bands", "modes", "scoring", "period")
        self._tree = ttk.Treeview(tf, columns=cols, show="headings",
                                   selectmode="browse", height=16)
        for col, hdr, w in [("id","ID",130), ("name","Nume",200),
                              ("type","Tip",80), ("bands","Benzi",80),
                              ("modes","Moduri",70), ("scoring","Scorare",80),
                              ("period","Perioada",90)]:
            self._tree.heading(col, text=hdr)
            self._tree.column(col, width=w, anchor="w")

        vsb = ttk.Scrollbar(tf, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self._tree.bind("<Double-1>", lambda e: self._edit())
        self._tree.bind("<Delete>", lambda e: self._delete())

        # Butoane actiuni
        bf = tk.Frame(self, bg=TH["bg"])
        bf.pack(fill="x", padx=10, pady=4)

        btns_left = [
            ("+ Adauga", self._add,       TH["ok"]),
            ("Editeaza", self._edit,      TH["accent"]),
            ("Duplica",  self._duplicate, "#1a5276"),
            ("Sterge",   self._delete,    TH["err"]),
        ]
        btns_right = [
            ("Export JSON",      self._export_json,  TH["btn_bg"]),
            ("Import JSON",      self._import_json,  TH["btn_bg"]),
            ("radioamator.ro",   self._open_web,     "#1a5276"),
        ]
        lf = tk.Frame(bf, bg=TH["bg"]); lf.pack(side="left")
        rf = tk.Frame(bf, bg=TH["bg"]); rf.pack(side="right")

        for txt, cmd, col in btns_left:
            tk.Button(lf, text=txt, command=cmd, bg=col, fg="white",
                      font=fn).pack(side="left", padx=3)
        for txt, cmd, col in btns_right:
            tk.Button(rf, text=txt, command=cmd, bg=col, fg="white",
                      font=fn).pack(side="left", padx=3)

        # Descriere concurs selectat
        self._desc = tk.Label(self, text="", bg=TH["bg"], fg="#888888",
                               font=("Consolas", 9), anchor="w", wraplength=750)
        self._desc.pack(fill="x", padx=12, pady=2)
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        # Salvare / Inchide
        bf2 = tk.Frame(self, bg=TH["bg"]); bf2.pack(pady=6)
        tk.Button(bf2, text="Salveaza si Inchide", command=self._save,
                  bg=TH["ok"], fg="white", font=("Consolas",11,"bold")).pack(side="left", padx=6)
        tk.Button(bf2, text="Inchide fara salvare", command=self.destroy,
                  bg=TH["btn_bg"], fg="white", font=("Consolas",10)).pack(side="left", padx=6)

    def _fill(self):
        for item in self._tree.get_children():
            self._tree.delete(item)
        lang = i18n.get_lang()
        for cid, cd in self._c.items():
            name = cd.get(f"name_{lang}", cd.get("name_ro", cid))
            bands = ",".join(cd.get("allowed_bands", [])[:3])
            if len(cd.get("allowed_bands", [])) > 3:
                bands += "..."
            modes = "+".join(cd.get("allowed_modes", [])[:3])
            is_def = " *" if cd.get("is_default") else ""
            self._tree.insert("", "end", iid=cid, values=(
                cid + is_def, name,
                cd.get("contest_type",""),
                bands, modes,
                cd.get("scoring_mode",""),
                cd.get("period",""),
            ))

    def _sel_id(self) -> str | None:
        sel = self._tree.selection()
        if not sel: return None
        return sel[0].rstrip(" *").strip()

    def _on_select(self, e=None):
        cid = self._sel_id()
        if cid and cid in self._c:
            desc = self._c[cid].get("description","")
            org  = self._c[cid].get("organizer","")
            txt = desc
            if org: txt += f"  |  Organizator: {org}"
            self._desc.config(text=txt)

    def _add(self):
        dlg = ContestEditor(self, cid=None, cdata=None, all_c=self._c)
        self.wait_window(dlg)
        if dlg.result:
            new_id, new_data = dlg.result
            self._c[new_id] = new_data
            self._fill()
            try: self._tree.selection_set(new_id)
            except: pass

    def _edit(self):
        cid = self._sel_id()
        if not cid: messagebox.showinfo("Manager", "Selectati un concurs!"); return
        dlg = ContestEditor(self, cid=cid, cdata=copy.deepcopy(self._c[cid]),
                             all_c=self._c)
        self.wait_window(dlg)
        if dlg.result:
            new_id, new_data = dlg.result
            if new_id != cid:
                del self._c[cid]
            self._c[new_id] = new_data
            self._fill()
            try: self._tree.selection_set(new_id)
            except: pass

    def _duplicate(self):
        cid = self._sel_id()
        if not cid: messagebox.showinfo("Manager", "Selectati un concurs!"); return
        new_id = cid + "_copia"
        counter = 2
        while new_id in self._c:
            new_id = f"{cid}_copia{counter}"; counter += 1
        new_data = copy.deepcopy(self._c[cid])
        new_data["is_default"] = False
        new_data["name_ro"] = new_data.get("name_ro","") + " (copie)"
        new_data["name_en"] = new_data.get("name_en","") + " (copy)"
        self._c[new_id] = new_data
        self._fill()
        try: self._tree.selection_set(new_id)
        except: pass

    def _delete(self):
        cid = self._sel_id()
        if not cid: return
        if self._c.get(cid, {}).get("is_default"):
            messagebox.showwarning("Manager", "Concursurile implicite nu pot fi sterse!")
            return
        if messagebox.askyesno("Manager", f"Sterge concursul '{cid}'?"):
            del self._c[cid]
            self._fill()

    def _export_json(self):
        cid = self._sel_id()
        if not cid: messagebox.showinfo("Export", "Selectati un concurs!"); return
        fp = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON","*.json")],
            initialfile=f"contest_{cid}.json")
        if fp:
            with open(fp, "w", encoding="utf-8") as f:
                json.dump({cid: self._c[cid]}, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Export", f"Exportat: {os.path.basename(fp)}")

    def _import_json(self):
        fp = filedialog.askopenfilename(filetypes=[("JSON","*.json")])
        if not fp: return
        try:
            with open(fp, encoding="utf-8") as f:
                data = json.load(f)
            imported = 0
            for cid, cdata in data.items():
                cdata["is_default"] = False
                self._c[cid] = cdata
                imported += 1
            self._fill()
            messagebox.showinfo("Import", f"Importate {imported} concurs(uri).")
        except Exception as e:
            messagebox.showerror("Import", f"Eroare: {e}")

    def _open_web(self):
        import webbrowser, threading
        threading.Thread(target=webbrowser.open_new_tab,
                         args=("https://www.radioamator.ro/contest/",),
                         daemon=True).start()

    def _save(self):
        self.result = self._c
        self.destroy()


class ContestEditor(tk.Toplevel):
    """Editor complet pentru un concurs: toate campurile editabile."""

    def __init__(self, parent, cid: str | None, cdata: dict | None,
                 all_c: dict | None = None):
        super().__init__(parent)
        self.result = None
        self._all_c = all_c or {}
        self._orig_id = cid

        # Date initiale
        self._data = cdata or {
            "name_ro": "", "name_en": "",
            "contest_type": "Concurs", "cabrillo_name": "",
            "categories": ["Individual"],
            "scoring_mode": "per_qso", "points_per_qso": 1,
            "min_qso": 0,
            "allowed_bands": list(BANDS_ALL),
            "allowed_modes": ["SSB","CW","FM"],
            "required_stations": [], "special_scoring": {},
            "use_serial": True, "use_county": True,
            "county_list": list(COUNTIES),
            "multiplier_type": "county", "band_points": {},
            "exchange_format": "serial",
            "period": "", "organizer": "",
            "description": "", "is_default": False,
        }

        title = f"Editeaza: {cid}" if cid else "Concurs Nou"
        self.title(title)
        _rg(self, parent, 820, 700)
        self.configure(bg=TH["bg"])
        self.transient(parent)
        self.grab_set()
        self._build(cid)

    def _build(self, cid: str | None):
        fn  = ("Consolas", 10)
        fnb = ("Consolas", 10, "bold")
        lo  = {"bg": TH["bg"], "fg": TH["fg"], "font": fn}
        eo  = {"bg": TH["entry_bg"], "fg": TH["fg"], "font": fn,
               "insertbackground": TH["fg"]}

        # Titlu
        label_title = "Editare Concurs" if cid else "Concurs Nou"
        tk.Label(self, text=label_title, bg=TH["bg"], fg=TH["gold"],
                 font=("Consolas",12,"bold")).pack(pady=(8,4))

        # Notebook cu taburi
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=4)

        # ── Tab 1: General ─────────────────────────────────────────────────
        t1 = tk.Frame(nb, bg=TH["bg"]); nb.add(t1, text="  General  ")
        gf = tk.Frame(t1, bg=TH["bg"]); gf.pack(fill="x", padx=12, pady=8)
        gf.columnconfigure(1, weight=1); gf.columnconfigure(3, weight=1)

        def lbl_ent(parent, row, col, text, key, width=20, upper=False):
            tk.Label(parent, text=text+":", **lo).grid(
                row=row, column=col*2, sticky="e", padx=(8,4), pady=3)
            e = tk.Entry(parent, width=width, **eo)
            e.insert(0, str(self._data.get(key,"")))
            e.grid(row=row, column=col*2+1, sticky="ew", padx=(0,8), pady=3)
            if upper:
                e.bind("<KeyRelease>", lambda ev, en=e:
                    (en.delete(0,"end"), en.insert(0, ev.widget.get().upper()),
                     en.icursor(min(ev.widget.index(tk.INSERT), len(ev.widget.get())))
                    ) if False else None)
            return e

        self._e = {}
        self._e["id"]       = lbl_ent(gf, 0, 0, "ID concurs", "id", 18)
        # ID vine din parametrul cid, nu din data
        self._e["id"].delete(0,"end")
        self._e["id"].insert(0, cid or "")

        self._e["name_ro"]  = lbl_ent(gf, 0, 1, "Nume RO", "name_ro", 22)
        self._e["name_en"]  = lbl_ent(gf, 1, 0, "Nume EN", "name_en", 18)
        self._e["cab_name"] = lbl_ent(gf, 1, 1, "Cabrillo Name", "cabrillo_name", 22)
        self._e["c_type"]   = lbl_ent(gf, 2, 0, "Tip concurs", "contest_type", 18)
        self._e["period"]   = lbl_ent(gf, 2, 1, "Perioada", "period", 22)
        self._e["organizer"]= lbl_ent(gf, 3, 0, "Organizator", "organizer", 18)

        # Categorii
        tk.Label(t1, text="Categorii (una pe linie):", **lo).pack(
            anchor="w", padx=14, pady=(6,0))
        self._cats_txt = tk.Text(t1, height=4, width=60, **eo)
        self._cats_txt.pack(padx=14, pady=2, fill="x")
        self._cats_txt.insert("1.0", "\n".join(self._data.get("categories",["Individual"])))

        # Descriere
        tk.Label(t1, text="Descriere:", **lo).pack(anchor="w", padx=14, pady=(4,0))
        self._desc_e = tk.Entry(t1, width=70, **eo)
        self._desc_e.insert(0, self._data.get("description",""))
        self._desc_e.pack(padx=14, pady=2, fill="x")

        # ── Tab 2: Scorare ─────────────────────────────────────────────────
        t2 = tk.Frame(nb, bg=TH["bg"]); nb.add(t2, text="  Scorare  ")
        sf = tk.Frame(t2, bg=TH["bg"]); sf.pack(fill="x", padx=12, pady=8)
        sf.columnconfigure(1, weight=1)

        # Mod scorare
        tk.Label(sf, text="Mod scorare:", **lo).grid(row=0,column=0,sticky="e",padx=(8,4),pady=4)
        self._scoring_v = tk.StringVar(value=self._data.get("scoring_mode","per_qso"))
        scoring_opts = ["none","per_qso","per_band","maraton","distance"]
        ttk.Combobox(sf, textvariable=self._scoring_v, values=scoring_opts,
                     state="readonly", width=18, font=fn).grid(
                         row=0,column=1,sticky="w",padx=(0,8),pady=4)

        tk.Label(sf, text="Puncte/QSO:", **lo).grid(row=1,column=0,sticky="e",padx=(8,4),pady=4)
        self._pts_e = tk.Entry(sf, width=6, **eo)
        self._pts_e.insert(0, str(self._data.get("points_per_qso",1)))
        self._pts_e.grid(row=1,column=1,sticky="w",padx=(0,8),pady=4)

        tk.Label(sf, text="Min QSO:", **lo).grid(row=2,column=0,sticky="e",padx=(8,4),pady=4)
        self._minqso_e = tk.Entry(sf, width=6, **eo)
        self._minqso_e.insert(0, str(self._data.get("min_qso",0)))
        self._minqso_e.grid(row=2,column=1,sticky="w",padx=(0,8),pady=4)

        # Multiplicatori
        tk.Label(sf, text="Multiplicatori:", **lo).grid(row=3,column=0,sticky="e",padx=(8,4),pady=4)
        self._mult_v = tk.StringVar(value=self._data.get("multiplier_type","none"))
        mult_opts = ["none","county","dxcc","grid","band"]
        ttk.Combobox(sf, textvariable=self._mult_v, values=mult_opts,
                     state="readonly", width=18, font=fn).grid(
                         row=3,column=1,sticky="w",padx=(0,8),pady=4)

        # Exchange format
        tk.Label(sf, text="Exchange format:", **lo).grid(row=4,column=0,sticky="e",padx=(8,4),pady=4)
        self._exch_v = tk.StringVar(value=self._data.get("exchange_format","serial"))
        exch_opts = ["none","serial","county","serial_county","grid","serial_grid"]
        ttk.Combobox(sf, textvariable=self._exch_v, values=exch_opts,
                     state="readonly", width=18, font=fn).grid(
                         row=4,column=1,sticky="w",padx=(0,8),pady=4)

        # Checkboxes
        cf = tk.Frame(t2, bg=TH["bg"]); cf.pack(fill="x", padx=14, pady=4)
        self._serial_v = tk.BooleanVar(value=self._data.get("use_serial",True))
        self._county_v = tk.BooleanVar(value=self._data.get("use_county",True))
        tk.Checkbutton(cf, text="Numere seriale", variable=self._serial_v,
                       bg=TH["bg"], fg=TH["fg"], selectcolor=TH["entry_bg"],
                       font=fn, activebackground=TH["bg"]).pack(side="left", padx=8)
        tk.Checkbutton(cf, text="Judete in exchange", variable=self._county_v,
                       bg=TH["bg"], fg=TH["fg"], selectcolor=TH["entry_bg"],
                       font=fn, activebackground=TH["bg"]).pack(side="left", padx=8)

        # Puncte per banda
        tk.Label(t2, text="Puncte per banda (JSON ex: {\"80m\":4,\"40m\":3}):",
                 **lo).pack(anchor="w", padx=14, pady=(8,0))
        self._bpts_e = tk.Entry(t2, width=55, **eo)
        bp = self._data.get("band_points",{})
        self._bpts_e.insert(0, json.dumps(bp) if bp else "{}")
        self._bpts_e.pack(padx=14, pady=2, fill="x")

        # Special scoring
        tk.Label(t2, text="Scorare speciala (JSON ex: {\"YO8\":3,\"YO\":1}):",
                 **lo).pack(anchor="w", padx=14, pady=(4,0))
        self._sspec_e = tk.Entry(t2, width=55, **eo)
        ss = self._data.get("special_scoring",{})
        self._sspec_e.insert(0, json.dumps(ss) if ss else "{}")
        self._sspec_e.pack(padx=14, pady=2, fill="x")

        # ── Tab 3: Benzi si Moduri ──────────────────────────────────────────
        t3 = tk.Frame(nb, bg=TH["bg"]); nb.add(t3, text="  Benzi & Moduri  ")
        bmf = tk.Frame(t3, bg=TH["bg"]); bmf.pack(fill="both", expand=True, padx=12, pady=8)

        # Benzi
        bf3 = tk.LabelFrame(bmf, text=" Benzi permise ", bg=TH["bg"],
                             fg=TH["gold"], font=fn, padx=6, pady=6)
        bf3.pack(side="left", fill="both", expand=True, padx=(0,6))
        self._band_vars = {}
        allowed_bands = self._data.get("allowed_bands", list(BANDS_ALL))
        for i, band in enumerate(BANDS_ALL):
            v = tk.BooleanVar(value=(band in allowed_bands))
            self._band_vars[band] = v
            tk.Checkbutton(bf3, text=band, variable=v,
                           bg=TH["bg"], fg=TH["fg"],
                           selectcolor=TH["entry_bg"], font=fn,
                           activebackground=TH["bg"]).grid(
                               row=i%8, column=i//8, sticky="w", padx=4)
        # Butoane selectie rapida benzi
        bqf = tk.Frame(bf3, bg=TH["bg"])
        bqf.grid(row=8, column=0, columnspan=3, pady=4)
        for txt, bands in [("HF", ["160m","80m","60m","40m","30m","20m","17m","15m","12m","10m"]),
                           ("VHF+", ["2m","70cm","23cm"]),
                           ("Toate", list(BANDS_ALL)),
                           ("Nici una", [])]:
            def _sel(b=bands):
                for bd, v in self._band_vars.items(): v.set(bd in b)
            tk.Button(bqf, text=txt, command=_sel, bg=TH["btn_bg"],
                      fg="white", font=("Consolas",8)).pack(side="left", padx=2)

        # Moduri
        mf3 = tk.LabelFrame(bmf, text=" Moduri permise ", bg=TH["bg"],
                             fg=TH["gold"], font=fn, padx=6, pady=6)
        mf3.pack(side="right", fill="both", padx=(6,0))
        self._mode_vars = {}
        allowed_modes = self._data.get("allowed_modes", list(MODES_ALL))
        for i, mode in enumerate(MODES_ALL):
            v = tk.BooleanVar(value=(mode in allowed_modes))
            self._mode_vars[mode] = v
            tk.Checkbutton(mf3, text=mode, variable=v,
                           bg=TH["bg"], fg=TH["fg"],
                           selectcolor=TH["entry_bg"], font=fn,
                           activebackground=TH["bg"]).grid(
                               row=i, column=0, sticky="w", padx=4)

        # ── Tab 4: Judete ───────────────────────────────────────────────────
        t4 = tk.Frame(nb, bg=TH["bg"]); nb.add(t4, text="  Judete  ")
        tk.Label(t4, text="Judete valide ca multiplicatori:",
                 bg=TH["bg"], fg=TH["fg"], font=fn).pack(anchor="w", padx=12, pady=(8,2))

        jf = tk.Frame(t4, bg=TH["bg"]); jf.pack(fill="x", padx=12)
        self._county_vars = {}
        county_list = self._data.get("county_list", list(COUNTIES))
        for i, jud in enumerate(COUNTIES):
            v = tk.BooleanVar(value=(jud in county_list))
            self._county_vars[jud] = v
            tk.Checkbutton(jf, text=jud, variable=v,
                           bg=TH["bg"], fg=TH["fg"],
                           selectcolor=TH["entry_bg"],
                           font=("Consolas",9),
                           activebackground=TH["bg"]).grid(
                               row=i//10, column=i%10, sticky="w")

        jqf = tk.Frame(t4, bg=TH["bg"]); jqf.pack(pady=6)
        tk.Button(jqf, text="Toate", bg=TH["ok"], fg="white", font=fn,
                  command=lambda: [v.set(True) for v in self._county_vars.values()]).pack(side="left",padx=4)
        tk.Button(jqf, text="Nici unul", bg=TH["err"], fg="white", font=fn,
                  command=lambda: [v.set(False) for v in self._county_vars.values()]).pack(side="left",padx=4)
        # Moldova (YO8)
        MOLDOVA = ["BC","BT","GL","IS","NT","SV","VS","VN"]
        tk.Button(jqf, text="Moldova", bg="#1a5276", fg="white", font=fn,
                  command=lambda: [v.set(j in MOLDOVA) for j,v in self._county_vars.items()]).pack(side="left",padx=4)

        # Butoane OK/Cancel
        bf_ok = tk.Frame(self, bg=TH["bg"]); bf_ok.pack(pady=8)
        tk.Button(bf_ok, text="OK - Salveaza", command=self._ok,
                  bg=TH["ok"], fg="white", font=("Consolas",11,"bold")).pack(side="left", padx=6)
        tk.Button(bf_ok, text="Anuleaza", command=self.destroy,
                  bg=TH["btn_bg"], fg="white", font=("Consolas",10)).pack(side="left", padx=6)

    def _ok(self):
        # Validare ID
        new_id = self._e["id"].get().strip().lower().replace(" ","_")
        if not new_id:
            messagebox.showwarning("Editor", "ID concurs obligatoriu!"); return
        if new_id != self._orig_id and new_id in self._all_c:
            messagebox.showwarning("Editor", f"ID '{new_id}' exista deja!"); return

        # Parsare band_points
        try:
            bp = json.loads(self._bpts_e.get().strip() or "{}")
        except Exception:
            bp = {}

        # Parsare special_scoring
        try:
            ss = json.loads(self._sspec_e.get().strip() or "{}")
        except Exception:
            ss = {}

        # Categorii
        cats_raw = self._cats_txt.get("1.0","end").strip()
        cats = [c.strip() for c in cats_raw.splitlines() if c.strip()]
        if not cats: cats = ["Individual"]

        data = {
            "name_ro":         self._e["name_ro"].get().strip(),
            "name_en":         self._e["name_en"].get().strip(),
            "contest_type":    self._e["c_type"].get().strip(),
            "cabrillo_name":   self._e["cab_name"].get().strip().upper(),
            "categories":      cats,
            "scoring_mode":    self._scoring_v.get(),
            "points_per_qso":  int(self._pts_e.get() or "1"),
            "min_qso":         int(self._minqso_e.get() or "0"),
            "allowed_bands":   [b for b,v in self._band_vars.items() if v.get()],
            "allowed_modes":   [m for m,v in self._mode_vars.items() if v.get()],
            "required_stations": [],
            "special_scoring": ss,
            "use_serial":      self._serial_v.get(),
            "use_county":      self._county_v.get(),
            "county_list":     [j for j,v in self._county_vars.items() if v.get()],
            "multiplier_type": self._mult_v.get(),
            "band_points":     bp,
            "exchange_format": self._exch_v.get(),
            "period":          self._e["period"].get().strip(),
            "organizer":       self._e["organizer"].get().strip(),
            "description":     self._desc_e.get().strip(),
            "is_default":      False,
        }

        self.result = (new_id, data)
        self.destroy()
