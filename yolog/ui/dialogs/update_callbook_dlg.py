# -*- coding: utf-8 -*-
"""
ui/dialogs/update_callbook_dlg.py
Dialog GUI pentru actualizarea bazei de date Callbook ANCOM offline.

Flux:
  1. Utilizatorul descarca fisierele XLSX noi de pe ancom.ro
  2. Selecteaza fisierele in acest dialog
  3. Apasa Actualizeaza -> se genereaza callbook_local.json nou
  4. Aplicatia foloseste automat baza noua la urmatoarea pornire
"""
from __future__ import annotations
import os, sys, json, threading, datetime, tkinter as tk
from tkinter import filedialog, scrolledtext, ttk
from ..theme import TH

ANCOM_URL_CALLBOOK  = "https://www.ancom.ro/category/autorizare-ro/radioamatori/"
ANCOM_URL_DIRECT    = "https://www.ancom.ro/uploads/links_files/Callbook.xlsx"

INSTRUCTIONS = """CUM SE ACTUALIZEAZA BAZA CALLBOOK ANCOM
========================================

PASUL 1 — Descarca fisierele XLSX noi de pe ANCOM:
  Site: https://www.ancom.ro/category/autorizare-ro/radioamatori/
  Sau apasa butonul "Deschide ANCOM.ro" de mai jos.

  Cauta si descarca:
    a) Callbook_DD_MM_YYYY.xlsx          (indicative radioamatori)
    b) Callbook_repetoare_DD_MM_YYYY.xlsx (repetoare)

PASUL 2 — Selecteaza fisierele in acest dialog:
  Apasa "Alege..." langa fiecare camp si selecteaza fisierul descarcat.

PASUL 3 — Apasa "Actualizeaza Callbook":
  Se proceseaza fisierele si se genereaza callbook_local.json nou.
  Procesul dureaza 10-30 secunde.

PASUL 4 — Gata!
  Inchide si reporneste YO Log PRO pentru a folosi baza noua.
  Sau foloseste direct Callbook Lookup -> baza locala ANCOM.

NOTA:
  Fisierele XLSX trebuie sa aiba coloanele standard ANCOM.
  Baza curenta NU se pierde daca actualizarea esueaza.
  Fisierul generat: network/callbook_local.json
"""


def _rg(d, p, iw, ih):
    try: sw, sh = d.winfo_screenwidth(), d.winfo_screenheight()
    except: sw, sh = 1366, 768
    w, h = min(iw, int(sw*.92)), min(ih, int(sh*.88))
    try:
        d.update_idletasks()
        x = max(10, min(p.winfo_rootx()+(p.winfo_width()-w)//2,  sw-w-10))
        y = max(10, min(p.winfo_rooty()+(p.winfo_height()-h)//2, sh-h-10))
    except:
        x, y = (sw-w)//2, (sh-h)//2
    d.geometry(f"{w}x{h}+{x}+{y}")


class UpdateCallbookDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Actualizare Callbook ANCOM")
        _rg(self, parent, 720, 620)
        self.configure(bg=TH["bg"])
        self.transient(parent)
        self.resizable(True, True)
        self._build()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build(self):
        fn  = ("Consolas", 10)
        fnb = ("Consolas", 11, "bold")

        # Titlu
        tk.Label(self,
                 text="Actualizare Baza Callbook ANCOM",
                 bg=TH["bg"], fg=TH["gold"], font=("Consolas", 13, "bold")
                 ).pack(pady=(10, 4))

        tk.Label(self,
                 text="Baza locala cu 4.964+ indicative YO + 437+ repetoare",
                 bg=TH["bg"], fg=TH["fg"], font=("Consolas", 9)
                 ).pack(pady=(0, 8))

        # Stare baza curenta
        self._info_lbl = tk.Label(self, text="",
                                   bg=TH["bg"], fg="#888888",
                                   font=("Consolas", 9))
        self._info_lbl.pack(anchor="w", padx=14)
        self._refresh_current_info()

        tk.Frame(self, bg=TH["accent"], height=1).pack(fill="x", padx=14, pady=6)

        # ── Sectiune fisiere ─────────────────────────────────────────────────
        ff = tk.LabelFrame(self, text=" Fisiere XLSX ANCOM ",
                           bg=TH["bg"], fg=TH["gold"], font=fn, padx=8, pady=8)
        ff.pack(fill="x", padx=14, pady=4)
        ff.columnconfigure(1, weight=1)

        # Callbook
        tk.Label(ff, text="Callbook:", bg=TH["bg"], fg=TH["fg"],
                 font=fn, anchor="e", width=12).grid(row=0, column=0, sticky="e", pady=4)
        self._cb_var = tk.StringVar()
        tk.Entry(ff, textvariable=self._cb_var, bg=TH["entry_bg"], fg=TH["fg"],
                 font=fn, state="readonly").grid(row=0, column=1, sticky="ew", padx=6)
        tk.Button(ff, text="Alege...", command=self._pick_callbook,
                  bg=TH["accent"], fg="white", font=fn).grid(row=0, column=2, padx=4)

        # Repetoare
        tk.Label(ff, text="Repetoare:", bg=TH["bg"], fg=TH["fg"],
                 font=fn, anchor="e", width=12).grid(row=1, column=0, sticky="e", pady=4)
        self._rep_var = tk.StringVar()
        tk.Entry(ff, textvariable=self._rep_var, bg=TH["entry_bg"], fg=TH["fg"],
                 font=fn, state="readonly").grid(row=1, column=1, sticky="ew", padx=6)
        tk.Button(ff, text="Alege...", command=self._pick_repetoare,
                  bg=TH["accent"], fg="white", font=fn).grid(row=1, column=2, padx=4)

        tk.Label(ff,
                 text="Descarca fisierele XLSX de pe ancom.ro (link-ul de mai jos)",
                 bg=TH["bg"], fg="#888888", font=("Consolas", 8)
                 ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(4, 0))

        # ── Butoane actiuni ──────────────────────────────────────────────────
        bf = tk.Frame(self, bg=TH["bg"]); bf.pack(fill="x", padx=14, pady=6)

        self._update_btn = tk.Button(
            bf, text="Actualizeaza Callbook",
            command=self._start_update,
            bg=TH["ok"], fg="white", font=fnb)
        self._update_btn.pack(side="left", padx=(0, 8))

        tk.Button(bf, text="Deschide ANCOM.ro",
                  command=lambda: __import__('threading').Thread(
                      target=__import__('webbrowser').open_new_tab,
                      args=(ANCOM_URL_CALLBOOK,), daemon=True).start(),
                  bg="#1a5276", fg="white", font=fn).pack(side="left", padx=4)

        tk.Button(bf, text="Inchide",
                  command=self.destroy,
                  bg=TH["btn_bg"], fg="white", font=fn).pack(side="right")

        # ── Progress bar ─────────────────────────────────────────────────────
        self._progress = ttk.Progressbar(self, mode="indeterminate", length=400)
        self._progress.pack(fill="x", padx=14, pady=(0, 4))

        # ── Log output ───────────────────────────────────────────────────────
        tk.Label(self, text="Log procesare:",
                 bg=TH["bg"], fg=TH["fg"], font=fn, anchor="w"
                 ).pack(anchor="w", padx=14)

        self._log = scrolledtext.ScrolledText(
            self, bg=TH["entry_bg"], fg=TH["fg"],
            font=("Consolas", 9), height=10, state="disabled", wrap="word")
        self._log.pack(fill="both", expand=True, padx=14, pady=(2, 8))

        # ── Instructiuni ─────────────────────────────────────────────────────
        tk.Frame(self, bg=TH["accent"], height=1).pack(fill="x", padx=14, pady=2)
        instr_frame = tk.Frame(self, bg=TH["bg"]); instr_frame.pack(fill="x", padx=14, pady=4)

        tk.Label(instr_frame,
                 text="Instructiuni de utilizare:",
                 bg=TH["bg"], fg=TH["gold"], font=fnb).pack(anchor="w")

        instr_txt = scrolledtext.ScrolledText(
            instr_frame, bg=TH["entry_bg"], fg="#aaaaaa",
            font=("Consolas", 8), height=6, state="normal", wrap="word")
        instr_txt.insert("1.0", INSTRUCTIONS)
        instr_txt.config(state="disabled")
        instr_txt.pack(fill="x")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _refresh_current_info(self):
        """Afiseaza info despre baza curenta instalata."""
        try:
            from ...network.local_callbook import get_info
            info = get_info()
            if info["available"]:
                self._info_lbl.config(
                    text=f"Baza curenta: {info['callbook']:,} indicative + "
                         f"{info['repeaters']:,} repetoare | Data: {info['date']}",
                    fg=TH["ok"])
            else:
                self._info_lbl.config(
                    text="Baza curenta: nu exista (callbook_local.json lipsa)",
                    fg=TH["warn"])
        except Exception as e:
            self._info_lbl.config(text=f"Baza curenta: eroare - {e}", fg=TH["err"])

    def _pick_callbook(self):
        fp = filedialog.askopenfilename(
            title="Selecteaza Callbook ANCOM",
            filetypes=[("Excel", "*.xlsx *.xls"), ("Toate", "*.*")])
        if fp:
            self._cb_var.set(fp)
            self._log_msg(f"Callbook selectat: {os.path.basename(fp)}")

    def _pick_repetoare(self):
        fp = filedialog.askopenfilename(
            title="Selecteaza Callbook Repetoare ANCOM",
            filetypes=[("Excel", "*.xlsx *.xls"), ("Toate", "*.*")])
        if fp:
            self._rep_var.set(fp)
            self._log_msg(f"Repetoare selectate: {os.path.basename(fp)}")

    def _log_msg(self, msg: str, color: str = None):
        """Adauga mesaj in log output (thread-safe via after)."""
        def _do():
            self._log.config(state="normal")
            self._log.insert("end", f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}\n")
            if color:
                # Coloreaza ultima linie
                last_line = self._log.index("end-2l linestart")
                self._log.tag_add(color, last_line, "end-1c")
                self._log.tag_config(color, foreground=color)
            self._log.see("end")
            self._log.config(state="disabled")
        try:
            self.after(0, _do)
        except Exception:
            pass

    # ── Actualizare ───────────────────────────────────────────────────────────

    def _start_update(self):
        cb_path  = self._cb_var.get().strip()
        rep_path = self._rep_var.get().strip()

        if not cb_path:
            self._log_msg("EROARE: Selectati fisierul Callbook XLSX!", TH["err"])
            return
        if not rep_path:
            self._log_msg("EROARE: Selectati fisierul Repetoare XLSX!", TH["err"])
            return
        if not os.path.exists(cb_path):
            self._log_msg(f"EROARE: Fisier inexistent: {cb_path}", TH["err"])
            return
        if not os.path.exists(rep_path):
            self._log_msg(f"EROARE: Fisier inexistent: {rep_path}", TH["err"])
            return

        # Dezactivam butonul si pornim progress bar
        self._update_btn.config(state="disabled", text="Se proceseaza...")
        self._progress.start(10)
        self._log_msg("Incepe actualizarea callbook...")
        self._log_msg(f"  Callbook:  {os.path.basename(cb_path)}")
        self._log_msg(f"  Repetoare: {os.path.basename(rep_path)}")

        # Rulam in thread separat ca sa nu blocheze UI
        t = threading.Thread(
            target=self._do_update,
            args=(cb_path, rep_path),
            daemon=True)
        t.start()

    def _do_update(self, cb_path: str, rep_path: str):
        """Ruleaza in thread separat."""
        try:
            # Importam parsoarele din network.callbook_updater
            from ...network.callbook_updater import parse_callbook, parse_repeaters

            self._log_msg("Citesc fisierul Callbook...")
            callbook = parse_callbook(cb_path)
            self._log_msg(f"  -> {len(callbook):,} indicative citite")

            self._log_msg("Citesc fisierul Repetoare...")
            repeaters = parse_repeaters(rep_path)
            self._log_msg(f"  -> {len(repeaters):,} repetoare citite")

            # Determinam calea de output
            base_dir = os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))))
            out_path = os.path.join(base_dir, "network", "callbook_local.json")

            # Backup fisier vechi
            if os.path.exists(out_path):
                backup = out_path + ".bak"
                import shutil
                shutil.copy2(out_path, backup)
                self._log_msg(f"Backup salvat: callbook_local.json.bak")

            # Scriem JSON nou
            self._log_msg("Scriem callbook_local.json...")
            output = {
                "date":      datetime.date.today().isoformat(),
                "callbook":  callbook,
                "repeaters": repeaters,
            }
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(output, f, ensure_ascii=False, separators=(",", ":"))

            size_kb = os.path.getsize(out_path) // 1024
            self._log_msg(f"")
            self._log_msg(f"SUCCES! Callbook actualizat:")
            self._log_msg(f"  Fisier: {out_path}")
            self._log_msg(f"  Dimensiune: {size_kb} KB")
            self._log_msg(f"  Indicative: {len(callbook):,}")
            self._log_msg(f"  Repetoare:  {len(repeaters):,}")
            self._log_msg(f"  Data:       {datetime.date.today().isoformat()}")
            self._log_msg(f"")
            self._log_msg("Reporniti YO Log PRO pentru a folosi baza noua.")
            self.after(0, self._on_success)

        except ImportError:
            self._log_msg(
                "EROARE: pandas nu este instalat!\n"
                "Instalati: pip install pandas openpyxl", TH["err"])
            self.after(0, self._on_error)
        except FileNotFoundError as e:
            self._log_msg(f"EROARE: Fisier negasit: {e}", TH["err"])
            self.after(0, self._on_error)
        except Exception as e:
            self._log_msg(f"EROARE: {type(e).__name__}: {e}", TH["err"])
            self.after(0, self._on_error)

    def _on_success(self):
        self._progress.stop()
        self._progress.config(value=100)
        self._update_btn.config(
            state="normal", text="Actualizeaza Callbook",
            bg=TH["ok"])
        self._refresh_current_info()
        # Reincarcam callbook in memorie fara repornire
        try:
            from ...network import local_callbook
            local_callbook._reload()
            self._log_msg("Baza noua incarcata in memorie - nu e nevoie de repornire!")
        except Exception:
            pass

    def _on_error(self):
        self._progress.stop()
        self._update_btn.config(
            state="normal", text="Actualizeaza Callbook",
            bg=TH["err"])
