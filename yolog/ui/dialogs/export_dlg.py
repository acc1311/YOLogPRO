# -*- coding: utf-8 -*-
"""
ui/dialogs/export_dlg.py — Dialog Export cu selecție categorie și sortare cronologică
"""
from __future__ import annotations
import datetime, os, re, tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from ..theme import TH
from ... import i18n
from ...core.score import Score
from ...core.bands import BAND_FREQ, CAB2_MODE_MAP
from ...core.dxcc import DXCC
from ...core.locator import Loc


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


def _center(d, p=None):
    d.update_idletasks()
    dw, dh = d.winfo_reqwidth(), d.winfo_reqheight()
    if p and p.winfo_exists():
        x = p.winfo_rootx() + (p.winfo_width()-dw)//2
        y = p.winfo_rooty() + (p.winfo_height()-dh)//2
    else:
        x = (d.winfo_screenwidth()-dw)//2
        y = (d.winfo_screenheight()-dh)//2
    d.geometry(f"{dw}x{dh}+{max(0,x)}+{max(0,y)}")


# ═══════════════════════════════════════════════════════════
# Categorii standard pentru export
# ═══════════════════════════════════════════════════════════
EXPORT_CATEGORIES = [
    "A. Seniori YO",
    "B. YL",
    "C. Juniori YO",
    "D. Club",
    "E. DX",
    "F. Receptori"
]


class ExportDialog(tk.Toplevel):
    """
    Dialog principal export — cu selecție categorie și sortare cronologică.
    """

    def __init__(self, parent, log, cfg, contest,
                 cab3_dialog_cls=None, cab2_dialog_cls=None,
                 dm=None):
        super().__init__(parent)
        self._log      = log
        self._cfg      = cfg
        self._contest  = contest
        self._parent   = parent
        self._cab3_cls = cab3_dialog_cls
        self._cab2_cls = cab2_dialog_cls
        self._dm       = dm
        self._cid      = cfg.get("log_id", cfg.get("contest", "simplu"))

        self.title(i18n.t("export"))
        _rg(self, parent, 400, 500)
        self.configure(bg=TH["bg"])
        self.transient(parent)

        fn = ("Consolas", 11)
        tk.Label(self, text=" " + i18n.t("export"),
                 bg=TH["bg"], fg=TH["gold"],
                 font=("Consolas", 12, "bold")).pack(pady=(10, 6))

        # ═══════════════════════════════════════════════════════════
        # Secțiune selectare categorie
        # ═══════════════════════════════════════════════════════════
        self._build_category_selector(fn)

        # Separator vizual
        sep_frame = tk.Frame(self, bg=TH["bg"], height=2)
        sep_frame.pack(fill="x", padx=15, pady=8)
        tk.Frame(sep_frame, bg=TH["gold"], height=1).pack(fill="x")

        # Butoane export
        buttons = [
            ("Cabrillo 3.0 (.log)",  self._exp_cab3,  TH["accent"]),
            ("Cabrillo 2.0 (.log)",  self._exp_cab2,  TH["accent"]),
            ("ADIF 3.1 (.adi)",      self._exp_adif,  TH["accent"]),
            ("CSV (.csv)",           self._exp_csv,   TH["accent"]),
            ("EDI (.edi)",           self._exp_edi,   TH["accent"]),
            (i18n.t("exp_print"),    self._exp_print, TH["accent"]),
        ]
        for txt, cmd, color in buttons:
            tk.Button(self, text=txt, command=cmd,
                      bg=color, fg="white",
                      font=fn).pack(pady=4, padx=10)

        tk.Button(self, text=i18n.t("cancel"), command=self.destroy,
                  bg=TH["btn_bg"], fg="white", font=fn).pack(pady=8)

    # ═══════════════════════════════════════════════════════════
    # Selector Categorie
    # ═══════════════════════════════════════════════════════════

    def _build_category_selector(self, fn):
        """Construiește secțiunea de selectare categorie."""
        cat_frame = tk.LabelFrame(
            self, 
            text=" Categorie Export ",
            bg=TH["bg"], 
            fg=TH["gold"],
            font=("Consolas", 10, "bold"),
            padx=10, 
            pady=8
        )
        cat_frame.pack(pady=(5, 5), padx=15, fill="x")

        # Frame interior pentru layout
        inner = tk.Frame(cat_frame, bg=TH["bg"])
        inner.pack(fill="x")

        tk.Label(inner, text="Categorie:",
                 bg=TH["bg"], fg=TH["fg"],
                 font=fn).pack(side="left", padx=(0, 8))

        # Lista de categorii fixe
        self._categories = EXPORT_CATEGORIES
        self._cat_var = tk.StringVar()

        # Setează categoria salvată anterior sau prima categorie
        saved_cat = self._cfg.get("_export_category", "")
        if saved_cat and saved_cat in self._categories:
            self._cat_var.set(saved_cat)
        else:
            self._cat_var.set(self._categories[0])

        self._cat_combo = ttk.Combobox(
            inner,
            textvariable=self._cat_var,
            values=self._categories,
            state="readonly",
            font=fn,
            width=20
        )
        self._cat_combo.pack(side="left", fill="x", expand=True)

        # Indicație categorie selectată
        self._cat_info = tk.Label(
            cat_frame, 
            text="",
            bg=TH["bg"], 
            fg=TH.get("dim", "#888888"),
            font=("Consolas", 9)
        )
        self._cat_info.pack(anchor="w", pady=(5, 0))
        
        # Update info la schimbare
        self._cat_combo.bind("<<ComboboxSelected>>", self._on_category_change)
        self._update_category_info()

    def _on_category_change(self, event=None):
        """Handler pentru schimbarea categoriei."""
        self._update_category_info()
        # Salvează selecția în config pentru persistență
        self._cfg["_export_category"] = self._cat_var.get()

    def _update_category_info(self):
        """Actualizează informația despre categoria selectată."""
        cat = self._cat_var.get()
        cat_letter = self._get_category_letter(cat)
        cat_num = self._get_category_number(cat)
        self._cat_info.config(
            text=f"→ Litera: {cat_letter} | Nr. Cabrillo: {cat_num}"
        )

    def _get_selected_category(self) -> str:
        """Returnează categoria selectată pentru export."""
        return self._cat_var.get()

    def _get_category_letter(self, cat_val: str = None) -> str:
        """Extrage litera categoriei (A, B, C, D, E, F)."""
        if cat_val is None:
            cat_val = self._get_selected_category()
        
        if not cat_val:
            return "A"
        
        # Extrage prima literă
        m = re.match(r'^([A-Za-z])', cat_val)
        if m:
            return m.group(1).upper()
        
        return "A"

    def _get_category_number(self, cat_val: str = None) -> str:
        """Calculează numărul categoriei (A→1, B→2, C→3, D→4, E→5, F→6)."""
        letter = self._get_category_letter(cat_val)
        return str(ord(letter) - ord('A') + 1)

    def _get_category_name(self, cat_val: str = None) -> str:
        """Extrage numele categoriei fără literă (ex: 'Seniori YO')."""
        if cat_val is None:
            cat_val = self._get_selected_category()
        
        if not cat_val:
            return ""
        
        # Elimină "X. " de la început
        m = re.match(r'^[A-Za-z]\.\s*(.+)$', cat_val)
        if m:
            return m.group(1)
        
        return cat_val

    # ═══════════════════════════════════════════════════════════
    # Sortare cronologică
    # ═══════════════════════════════════════════════════════════

    def _get_sorted_log(self) -> list:
        """Returnează log-ul sortat cronologic după dată și oră."""
        return sorted(
            self._log,
            key=lambda q: (q.get("d", ""), q.get("t", ""))
        )

    # ═══════════════════════════════════════════════════════════
    # Verificare înainte de orice export
    # ═══════════════════════════════════════════════════════════

    def _check_before_export(self) -> bool:
        """Verifică log, avertizează la probleme, face backup automat."""
        if not self._log:
            messagebox.showwarning(i18n.t("error"), "Log gol!")
            return False
        ok, msg, _ = Score.validate(self._log, self._contest, self._cfg)
        if not ok:
            if not messagebox.askyesno(
                    i18n.t("exp_warn"),
                    i18n.t("exp_warn_msg").format(msg)):
                return False
        # Backup automat înainte de export
        if self._dm:
            self._dm.backup(self._cid, self._log)
        return True

    def _save_cfg(self):
        """Salvează preferințele în config.json."""
        if self._dm:
            self._dm.save("config.json", self._cfg)

    # ═══════════════════════════════════════════════════════════
    # Obține folder implicit pentru export
    # ═══════════════════════════════════════════════════════════

    def _get_export_dir(self) -> str:
        """Returnează ultimul folder folosit sau Desktop."""
        last_dir = self._cfg.get("_last_export_dir", "")
        if last_dir and os.path.isdir(last_dir):
            return last_dir
        
        # Încearcă Desktop
        desktop = os.path.expanduser("~/Desktop")
        if os.path.isdir(desktop):
            return desktop
        
        # Fallback la Documents
        docs = os.path.expanduser("~/Documents")
        if os.path.isdir(docs):
            return docs
        
        # Fallback la home
        return os.path.expanduser("~")

    # ═══════════════════════════════════════════════════════════
    # Cabrillo 3.0
    # ═══════════════════════════════════════════════════════════

    def _exp_cab3(self):
        if not self._check_before_export():
            return

        selected_cat = self._get_selected_category()
        self._cfg["_export_category"] = selected_cat

        if self._cab3_cls:
            cfg_dlg = self._cab3_cls(self._parent, self._cfg)
            self._parent.wait_window(cfg_dlg)
            if not cfg_dlg.result:
                return
            date_fmt = cfg_dlg.result["date_fmt"]
            operator = cfg_dlg.result["operator"]
            power    = cfg_dlg.result["power"]
            self._cfg["cab3_date_fmt"] = date_fmt
            self._cfg["cab3_operator"] = operator
            self._cfg["cab3_power"]    = power
            self._save_cfg()
        else:
            date_fmt = self._cfg.get("cab3_date_fmt", "no_dash")
            operator = self._cfg.get("cab3_operator", "SINGLE-OP")
            power    = self._cfg.get("cab3_power",    "HIGH")

        try:
            content = self._build_cab3(date_fmt, operator, power, selected_cat)
            ts  = datetime.datetime.now().strftime("%Y%m%d_%H%M")
            cid = self._cid
            cat_letter = self._get_category_letter(selected_cat)
            self._preview_and_save(
                content,
                f"cab3_{cid}_{cat_letter}_{ts}.log",
                [("Cabrillo", "*.log")],
                f"Cabrillo 3.0 [{selected_cat}]")
        except Exception as e:
            messagebox.showerror(i18n.t("error"), str(e))

    def _build_cab3(self, date_fmt, operator, power, category=None) -> str:
        """Construiește conținut Cabrillo 3.0 — sortat cronologic."""
        my   = self._cfg.get("call", "NOCALL")
        cc   = self._contest
        nm   = cc.get("cabrillo_name","") or cc.get("name_en", cc.get("name_ro","CONTEST"))
        ef   = cc.get("exchange_format","none")
        
        cat = category or self._get_selected_category()
        cat_num = self._get_category_number(cat)
        cat_letter = self._get_category_letter(cat)
        cat_name = self._get_category_name(cat)

        lines = [
            "START-OF-LOG: 3.0",
            f"CONTEST: {nm}",
            f"CALLSIGN: {my}",
            f"GRID-LOCATOR: {self._cfg.get('loc','')}",
            f"CATEGORY-OPERATOR: {operator}",
            "CATEGORY-BAND: ALL",
            f"CATEGORY-POWER: {power}",
            "CATEGORY-MODE: MIXED",
            f"CATEGORY: {cat_num}",
            "CATEGORY-ASSISTED: NON-ASSISTED",
            f"NAME: {self._cfg.get('op_name','')}",
            f"ADDRESS: {self._cfg.get('addr','')}",
            f"SOAPBOX: Category {cat_letter}: {cat_name}",
            "SOAPBOX: Logged with YO Log PRO v19",
            f"SOAPBOX: {self._cfg.get('soapbox','73 GL')}",
            "CREATED-BY: YO Log PRO v19",
        ]
        
        # Sortare cronologică după dată și oră
        sorted_log = self._get_sorted_log()
        
        for q in sorted_log:
            freq = self._resolve_freq(q)
            es   = self._resolve_exchange_sent(q, ef)
            er   = self._resolve_exchange_rcvd(q, "log")
            date = self._format_date(q.get("d",""), date_fmt)
            time_raw = q.get("t","").replace(":", "")
            time = time_raw[:4] if len(time_raw) >= 4 else time_raw
            lines.append(
                f"QSO: {freq:>6} {q.get('m','SSB'):<5} {date} {time} "
                f"{my:<13} {q.get('s','59'):<4} {es:<10} "
                f"{q.get('c',''):<13} {q.get('r','59'):<4} {er}")
        
        lines.append("END-OF-LOG:")
        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════════
    # Cabrillo 2.0
    # ═══════════════════════════════════════════════════════════

    def _exp_cab2(self):
        if not self._check_before_export():
            return

        selected_cat = self._get_selected_category()
        self._cfg["_export_category"] = selected_cat

        if self._cab2_cls:
            cfg_dlg = self._cab2_cls(self._parent, self._cfg)
            self._parent.wait_window(cfg_dlg)
            if not cfg_dlg.result:
                return
            exch_sent = cfg_dlg.result["sent"]
            exch_rcvd = cfg_dlg.result["rcvd"]
            date_fmt  = cfg_dlg.result.get("date_fmt","with_dash")
            self._cfg["cab2_exch_sent"] = exch_sent
            self._cfg["cab2_exch_rcvd"] = exch_rcvd
            self._cfg["cab2_date_fmt"]  = date_fmt
            self._save_cfg()
        else:
            exch_sent = self._cfg.get("cab2_exch_sent","none")
            exch_rcvd = self._cfg.get("cab2_exch_rcvd","log")
            date_fmt  = self._cfg.get("cab2_date_fmt","with_dash")

        try:
            content = self._build_cab2(exch_sent, exch_rcvd, date_fmt, selected_cat)
            ts  = datetime.datetime.now().strftime("%Y%m%d_%H%M")
            cid = self._cid
            cat_letter = self._get_category_letter(selected_cat)
            self._preview_and_save(
                content,
                f"cab2_{cid}_{cat_letter}_{ts}.log",
                [("Cabrillo", "*.log")],
                f"Cabrillo 2.0 [{selected_cat}]")
        except Exception as e:
            messagebox.showerror(i18n.t("error"), str(e))

    def _build_cab2(self, exch_sent, exch_rcvd, date_fmt, category=None) -> str:
        """Construiește conținut Cabrillo 2.0 — sortat cronologic."""
        my  = self._cfg.get("call","NOCALL")
        cc  = self._contest
        nm  = (cc.get("cabrillo_name","") or
               cc.get("name_en", cc.get("name_ro","CONTEST"))).upper()

        cat = category or self._get_selected_category()
        cat_num = self._get_category_number(cat)
        cat_letter = self._get_category_letter(cat)
        cat_name = self._get_category_name(cat)

        _, _, tot = Score.total(self._log, cc, self._cfg)

        lines = [
            "START-OF-LOG: 2.0",
            "CREATED BY: YO Log PRO v19",
            f"CONTEST: {nm}",
            f"CALLSIGN: {my}",
            f"NAME: {self._cfg.get('op_name','')}",
            f"CATEGORY: {cat_num}",
            f"CLAIMED-SCORE: {tot}",
            f"ADDRESS: {self._cfg.get('addr','')}",
            f"EMAIL: {self._cfg.get('email','')}",
            f"SOAPBOX: Category {cat_letter}: {cat_name}",
            "SOAPBOX: Logged with YO Log PRO v19",
            f"SOAPBOX: {self._cfg.get('soapbox','73 GL')}",
            "SOAPBOX:  mo  yyyy mm dd hhmm call         rs exc call          rs exc",
            "SOAPBOX:  ** ********** **** ************* **  ** ************* **  **",
        ]
        
        # Sortare cronologică după dată și oră
        sorted_log = self._get_sorted_log()
        
        for q in sorted_log:
            freq  = self._resolve_freq(q)
            mode  = CAB2_MODE_MAP.get(q.get("m","SSB"), "PH")
            date  = self._format_date(q.get("d",""), date_fmt)
            time_raw = q.get("t","").replace(":", "")
            time  = time_raw[:4] if len(time_raw) >= 4 else time_raw
            es    = self._resolve_exchange_sent(q, exch_sent)
            er    = self._resolve_exchange_rcvd(q, exch_rcvd)
            lines.append(
                f"QSO: {freq} {mode} {date} {time} "
                f"{my:<13} {q.get('s','59'):>2}  {es:<2} "
                f"{q.get('c',''):<13} {q.get('r','59'):>2}  {er:<2}")
        
        lines.append("END-OF-LOG:")
        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════════
    # Celelalte formate
    # ═══════════════════════════════════════════════════════════

    def _exp_adif(self):
        if not self._check_before_export():
            return
        self._cfg["_export_category"] = self._get_selected_category()
        try:
            from ...export.exporters import ADIFExporter
            content = ADIFExporter.export(self._log, self._cfg)
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M")
            cat_letter = self._get_category_letter()
            self._save_direct(content, f"adif_{cat_letter}_{ts}.adi", [("ADIF","*.adi")])
        except Exception as e:
            messagebox.showerror(i18n.t("error"), str(e))

    def _exp_csv(self):
        if not self._check_before_export():
            return
        self._cfg["_export_category"] = self._get_selected_category()
        try:
            from ...export.exporters import CSVExporter
            content = CSVExporter.export(self._log, self._cfg, self._contest)
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M")
            cat_letter = self._get_category_letter()
            self._save_direct(content, f"log_{cat_letter}_{ts}.csv", [("CSV","*.csv")])
        except Exception as e:
            messagebox.showerror(i18n.t("error"), str(e))

    def _exp_edi(self):
        if not self._check_before_export():
            return
        self._cfg["_export_category"] = self._get_selected_category()
        try:
            from ...export.exporters import EDIExporter
            content = EDIExporter.export(self._log, self._cfg, self._contest)
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M")
            cat_letter = self._get_category_letter()
            self._save_direct(content, f"edi_{cat_letter}_{ts}.edi", [("EDI","*.edi")])
        except Exception as e:
            messagebox.showerror(i18n.t("error"), str(e))

    def _exp_print(self):
        if not self._check_before_export():
            return
        self._cfg["_export_category"] = self._get_selected_category()
        try:
            from ...export.exporters import PrintExporter
            content = PrintExporter.export(self._log, self._cfg, self._contest)
            cid = self._cid
            ts  = datetime.datetime.now().strftime("%Y%m%d_%H%M")
            cat_letter = self._get_category_letter()
            self._save_direct(content, f"print_{cid}_{cat_letter}_{ts}.txt", [("Text","*.txt")])
        except Exception as e:
            messagebox.showerror(i18n.t("error"), str(e))

    # ═══════════════════════════════════════════════════════════
    # Preview + salvare
    # ═══════════════════════════════════════════════════════════

    def _preview_and_save(self, content, default_fn, filetypes, title_suffix=""):
        """Deschide PreviewDialog, din care utilizatorul salvează."""
        def do_save(text):
            self._save_direct(text, default_fn, filetypes)

        title = f"{i18n.t('preview_t')} — {title_suffix}"
        prev = tk.Toplevel(self._parent)
        prev.title(title)
        _rg(prev, self._parent, 780, 580)
        prev.configure(bg=TH["bg"])
        prev.transient(self._parent)

        # Info sortare cronologică
        info_lbl = tk.Label(
            prev,
            text=f"✓ {len(self._log)} QSO-uri sortate cronologic (dată + oră)",
            bg=TH["bg"],
            fg=TH.get("ok", "#4CAF50"),
            font=("Consolas", 9)
        )
        info_lbl.pack(pady=(5, 0))

        txt = scrolledtext.ScrolledText(
            prev, bg=TH["entry_bg"], fg=TH["fg"],
            font=("Consolas", 10), wrap="none")
        txt.pack(fill="both", expand=True, padx=10, pady=10)
        txt.insert("1.0", content)
        txt.config(state="disabled")

        bf = tk.Frame(prev, bg=TH["bg"]); bf.pack(pady=8)
        tk.Button(bf, text=i18n.t("save"),
                  command=lambda: [do_save(content), prev.destroy(), self.destroy()],
                  bg=TH["ok"], fg="white",
                  font=("Consolas", 12, "bold")).pack(side="left", padx=8)
        tk.Button(bf, text=i18n.t("cancel"), command=prev.destroy,
                  bg=TH["btn_bg"], fg="white",
                  font=("Consolas", 12)).pack(side="left", padx=8)
        _center(prev, self._parent)

    def _save_direct(self, content, default_fn, filetypes):
        """Salvare directă cu dialog filedialog + confirmare + memorare folder."""
        ext = default_fn.rsplit(".", 1)[-1]
        
        # Obține folderul implicit (ultimul folosit sau Desktop/Documents)
        initial_dir = self._get_export_dir()
        
        fp = filedialog.asksaveasfilename(
            initialdir=initial_dir,
            defaultextension=f".{ext}",
            filetypes=filetypes,
            initialfile=default_fn,
            title="Salvează fișierul exportat"
        )
        
        if fp:
            # Memorează folderul pentru exporturile viitoare
            self._cfg["_last_export_dir"] = os.path.dirname(fp)
            self._save_cfg()
            
            try:
                with open(fp, "w", encoding="utf-8") as f:
                    f.write(content)
                messagebox.showinfo(
                    i18n.t("exp_ok"), 
                    f"Fișier salvat cu succes!\n\n"
                    f"→ {os.path.basename(fp)}\n\n"
                    f"Locație: {os.path.dirname(fp)}\n\n"
                    f"QSO-uri exportate: {len(self._log)}"
                )
            except Exception as e:
                messagebox.showerror(i18n.t("error"), str(e))

    # ═══════════════════════════════════════════════════════════
    # Helpers
    # ═══════════════════════════════════════════════════════════

    def _resolve_freq(self, q) -> str:
        freq = q.get("f","") or str(BAND_FREQ.get(q.get("b",""), 0))
        try: return str(int(float(freq)))
        except: return freq

    def _format_date(self, d, fmt) -> str:
        d_raw = d.replace("-","")
        if len(d_raw) == 8:
            return f"{d_raw[:4]}-{d_raw[4:6]}-{d_raw[6:8]}" if fmt=="with_dash" else d_raw
        return d

    def _resolve_exchange_sent(self, q, mode) -> str:
        if mode == "county":  return self._cfg.get("county", self._cfg.get("jud","--"))
        if mode == "grid":    return self._cfg.get("loc","--")
        if mode == "serial":  return q.get("ss","") or "--"
        return "--"

    def _resolve_exchange_rcvd(self, q, mode) -> str:
        if mode == "log":
            return (q.get("sr","") or q.get("n","") or "--").strip()
        return "--"
