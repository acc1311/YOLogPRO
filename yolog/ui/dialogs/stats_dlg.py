# -*- coding: utf-8 -*-
"""ui/dialogs/stats_dlg.py — Statistici log imbunatatite v19"""
import datetime
import tkinter as tk
from tkinter import scrolledtext
from collections import Counter
from ..theme import TH
from ... import i18n
from ...core.score import Score
from ...core.dxcc import DXCC
from ...core.bands import BANDS_ALL


class StatsDialog(tk.Toplevel):
    def __init__(self, parent, log_data, rules, cfg):
        super().__init__(parent)
        self.title(i18n.t("stats"))
        try:
            sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        except Exception:
            sw, sh = 1366, 768
        w = min(640, int(sw * 0.9))
        h = min(620, int(sh * 0.88))
        try:
            x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
            y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
            x = max(10, min(x, sw - w - 10))
            y = max(10, min(y, sh - h - 10))
            self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            self.geometry(f"{w}x{h}")
        self.configure(bg=TH["bg"])
        self.transient(parent)
        self.resizable(True, True)

        txt = scrolledtext.ScrolledText(
            self, bg=TH["entry_bg"], fg=TH["fg"],
            font=("Consolas", 10), wrap="word",
        )
        txt.pack(fill="both", expand=True, padx=10, pady=10)
        txt.tag_configure("h1",  foreground=TH["gold"],    font=("Consolas", 12, "bold"))
        txt.tag_configure("h2",  foreground=TH["cyan"],    font=("Consolas", 10, "bold"))
        txt.tag_configure("ok",  foreground=TH["ok"])
        txt.tag_configure("warn",foreground=TH["warn"])
        txt.tag_configure("err", foreground=TH["err"])

        def w(t, tag=None):
            txt.insert("end", t, tag)

        # ─── Header ──────────────────────────────────────────────────────────
        nm = (rules.get(f"name_{i18n.get_lang()}", rules.get("name_ro", "?"))
              if rules else "?")
        call = cfg.get("call", "NOCALL")
        w(f" Statistici — {nm}\n", "h1")
        w(f" Statie: {call}  |  Locator: {cfg.get('loc','?')}\n\n")

        # ─── General ─────────────────────────────────────────────────────────
        w(" ─── General ───────────────────────────────────\n", "h2")
        total_qso  = len(log_data)
        uniq_calls = Score.unique_calls(log_data)
        w(f"  Total QSO    : {total_qso}\n")
        w(f"  Indicative unice : {uniq_calls}\n")

        # Durata si rata
        if log_data:
            try:
                dts = sorted([
                    datetime.datetime.strptime(
                        q.get("d","") + " " + q.get("t",""), "%Y-%m-%d %H:%M"
                    )
                    for q in log_data
                    if q.get("d") and q.get("t")
                ])
                if len(dts) >= 2:
                    span_h = (dts[-1] - dts[0]).total_seconds() / 3600
                    if span_h > 0:
                        rate = total_qso / span_h
                        w(f"  Durata log   : {span_h:.1f}h\n")
                        w(f"  Rata medie   : {rate:.1f} QSO/h\n")
                    w(f"  Primul QSO   : {dts[0].strftime('%Y-%m-%d %H:%M')} UTC\n")
                    w(f"  Ultimul QSO  : {dts[-1].strftime('%Y-%m-%d %H:%M')} UTC\n")
            except Exception:
                pass

        # ─── Benzi ───────────────────────────────────────────────────────────
        w("\n ─── Benzi ──────────────────────────────────────\n", "h2")
        band_summary = Score.band_summary(log_data)
        for b in BANDS_ALL:
            if b in band_summary:
                cnt = band_summary[b]
                pts = sum(Score.qso(q, rules, cfg) for q in log_data if q.get("b") == b)
                bar = "█" * min(30, cnt // max(1, total_qso // 30) if total_qso > 30 else cnt)
                if rules and rules.get("scoring_mode","none") != "none":
                    w(f"  {b:<6}  {cnt:>4} QSO  {pts:>6} pt  {bar}\n")
                else:
                    w(f"  {b:<6}  {cnt:>4} QSO  {bar}\n")

        # ─── Moduri ──────────────────────────────────────────────────────────
        w("\n ─── Moduri ─────────────────────────────────────\n", "h2")
        mode_summary = Score.mode_summary(log_data)
        for mode, cnt in sorted(mode_summary.items(), key=lambda x: -x[1]):
            pct = cnt * 100 // total_qso if total_qso else 0
            w(f"  {mode:<8}  {cnt:>4} QSO  ({pct}%)\n")

        # ─── Tari DXCC ───────────────────────────────────────────────────────
        countries: Counter = Counter()
        for q in log_data:
            c, _ = DXCC.lookup(q.get("c", ""))
            countries[c] += 1
        if countries:
            w("\n ─── Tari DXCC (top 10) ─────────────────────────\n", "h2")
            for country, cnt in countries.most_common(10):
                if country != "Unknown":
                    w(f"  {country:<20}  {cnt:>4} QSO\n")
            w(f"\n  Total tari unice: {len(countries)}\n")

        # ─── Scor ────────────────────────────────────────────────────────────
        w("\n ─── Scor Final ─────────────────────────────────\n", "h2")
        if rules and rules.get("scoring_mode", "none") != "none":
            qp, mult, tot = Score.total(log_data, rules, cfg)
            mult_type = rules.get("multiplier_type", "none")
            if mult_type != "none":
                w(f"  Puncte QSO  : {qp}\n")
                w(f"  Multiplicatori: {mult}\n")
                w(f"  SCOR TOTAL  : {qp} × {mult} = {tot}\n", "ok")
            else:
                w(f"  SCOR TOTAL  : {tot}\n", "ok")
        else:
            w("  (Log simplu — fara scorare)\n", "warn")

        # Duplicate
        seen: set = set()
        dups = 0
        for q in log_data:
            k = (q.get("c","").upper(), q.get("b"), q.get("m"))
            if k in seen:
                dups += 1
            seen.add(k)
        if dups:
            w(f"\n  ⚠ Duplicate detectate: {dups}\n", "warn")
        else:
            w("\n  ✅ Fara duplicate\n", "ok")

        txt.config(state="disabled")

        bf = tk.Frame(self, bg=TH["bg"])
        bf.pack(pady=(0, 8))
        tk.Button(
            bf, text=i18n.t("close"), command=self.destroy,
            bg=TH["ok"], fg="white", font=("Consolas", 10, "bold"), padx=12,
        ).pack()
