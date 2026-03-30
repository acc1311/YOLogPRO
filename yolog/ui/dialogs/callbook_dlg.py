# -*- coding: utf-8 -*-
"""
ui/dialogs/callbook_dlg.py — Fereastră Callbook Lookup
Surse: radioamator.ro (online) | QRZ.com (online) | ANCOM Local (offline)
Afiseaza pagina web reala folosind tkinterweb sau fallback date structurate.
"""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk, scrolledtext
import queue, logging, webbrowser, threading

from ..theme import TH
from ... import i18n
from ...network.callbook import CallbookService
from ...network.local_callbook import (lookup as local_lookup,
                                        search as local_search,
                                        get_info as local_info)

logger = logging.getLogger(__name__)

# tkinterweb dezactivat intentionat — HtmlFrame.load_url() blocheaza/inchide
# aplicatia pe Windows cand incarca pagini externe (bug cunoscut tkinterweb + Tkinter Win32).
# Folosim intotdeauna fallback-ul cu buton "Deschide in browser".
HAS_TKWEB = False

FIELD_LABELS = {
    "call": "Indicativ", "name": "Titular", "class": "Clasa",
    "qth": "Localitate", "county": "Judet", "email": "E-mail",
    "expires": "Expira", "dxcc": "DXCC", "loc": "Locator",
    "itu": "Zona ITU", "cq": "Zona CQ", "source": "Sursa",
    "owner": "Titular", "type": "Tip statie", "tx_freq": "Frecv. emisie",
    "rx_freq": "Frecv. receptie", "power": "Putere (dBW)",
    "emission": "Emisiune", "region": "Directie reg.",
    "lat": "Latitudine", "lon": "Longitudine",
}

SOURCES = ["ANCOM Local (offline)", "radioamator.ro", "QRZ.com"]

URL_TEMPLATES = {
    "radioamator.ro": "https://www.radioamator.ro/call-book/yocall.php?call={}",
    "QRZ.com":        "https://www.qrz.com/db/{}",
}


class CallbookWindow(tk.Toplevel):
    def __init__(self, parent, initial_call: str = ""):
        super().__init__(parent)
        self.title("Callbook Lookup")
        self._svc    = CallbookService()
        self._queue  = queue.Queue()
        self._parent = parent

        try:
            sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        except Exception:
            sw, sh = 1366, 768

        w = min(820, int(sw * .92))
        h = min(660, int(sh * .88))
        try:
            self.update_idletasks()
            x = max(10, min(parent.winfo_rootx() + (parent.winfo_width()  - w) // 2, sw - w - 10))
            y = max(10, min(parent.winfo_rooty() + (parent.winfo_height() - h) // 2, sh - h - 10))
            self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            self.geometry(f"{w}x{h}")

        self.configure(bg=TH["bg"])
        self.transient(parent)
        self._build()
        self._update_local_info()
        if initial_call:
            self._call_e.insert(0, initial_call.upper())
            self._lookup()
        self._process_queue()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build(self):
        fn = ("Consolas", 11)

        # ── Bara cautare ─────────────────────────────────────────────────────
        sf = tk.Frame(self, bg=TH["bg"]); sf.pack(fill="x", padx=10, pady=(10, 4))

        tk.Label(sf, text="Indicativ:", bg=TH["bg"], fg=TH["fg"], font=fn).pack(side="left")
        self._call_e = tk.Entry(sf, width=12, bg=TH["entry_bg"], fg=TH["gold"],
                                font=("Consolas", 13, "bold"),
                                insertbackground="white", justify="center")
        self._call_e.pack(side="left", padx=6)
        self._call_e.bind("<Return>", lambda e: self._lookup())
        self._call_e.bind("<KeyRelease>", self._on_key)
        self._call_e.focus_set()

        self._src_v = tk.StringVar(value=SOURCES[0])
        src_cb = ttk.Combobox(sf, textvariable=self._src_v, values=SOURCES,
                              state="readonly", width=22, font=fn)
        src_cb.pack(side="left", padx=4)
        src_cb.bind("<<ComboboxSelected>>", lambda e: self._on_source_change())

        tk.Button(sf, text="Cauta", command=self._lookup,
                  bg=TH["accent"], fg="white", font=fn).pack(side="left", padx=4)
        tk.Button(sf, text="Cautare live", command=self._search_live,
                  bg="#1a5276", fg="white", font=("Consolas", 10)).pack(side="left", padx=2)
        tk.Button(sf, text="Deschide in browser", command=self._open_browser,
                  bg="#37474f", fg="white", font=("Consolas", 9)).pack(side="left", padx=2)

        # Status
        self._status = tk.Label(self, text="", bg=TH["bg"], fg=TH["ok"],
                                font=("Consolas", 9))
        self._status.pack(anchor="w", padx=12)

        # ── Notebook: Date | Web | Cautare ───────────────────────────────────
        self._nb = ttk.Notebook(self)
        self._nb.pack(fill="both", expand=True, padx=10, pady=4)

        # Tab 1: Date structurate
        tab_data = tk.Frame(self._nb, bg=TH["bg"])
        self._nb.add(tab_data, text="  Date statie  ")

        self._fields_frame = tk.Frame(tab_data, bg=TH["bg"])
        self._fields_frame.pack(fill="x", padx=6, pady=6)
        self._info_labels: dict = {}
        self._build_fields({})

        self._extra_txt = scrolledtext.ScrolledText(
            tab_data, bg=TH["entry_bg"], fg=TH["fg"],
            font=("Consolas", 9), wrap="word", height=7, state="disabled")
        self._extra_txt.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        # Tab 2: Pagina Web
        tab_web = tk.Frame(self._nb, bg=TH["bg"])
        self._nb.add(tab_web, text="  Pagina Web  ")

        self._web_frame = None
        self._web_txt   = None

        if self._web_frame is None:
            # Fallback robust: afisare link + buton + deschidere automata
            wf = tk.Frame(tab_web, bg=TH["bg"]); wf.pack(fill="both", expand=True)

            tk.Label(wf, text="",
                     bg=TH["bg"], fg=TH["fg"]).pack(pady=20)

            tk.Label(wf,
                     text="Pagina Callbook",
                     bg=TH["bg"], fg=TH["gold"],
                     font=("Consolas", 14, "bold")).pack(pady=(0,8))

            self._web_url_lbl = tk.Label(wf, text="",
                                          bg=TH["bg"], fg="#4fa3e0",
                                          font=("Consolas", 10, "underline"),
                                          cursor="hand2")
            self._web_url_lbl.pack(pady=4)
            self._web_url_lbl.bind("<Button-1>", lambda e: self._open_browser())

            tk.Button(wf,
                      text="  Deschide in browser (radioamator.ro / QRZ.com)  ",
                      command=self._open_browser,
                      bg=TH["accent"], fg="white",
                      font=("Consolas", 11, "bold"),
                      cursor="hand2", pady=8).pack(pady=16)

            tk.Label(wf,
                     text="Apasati butonul pentru a deschide pagina completa in browserul implicit.",
                     bg=TH["bg"], fg=TH["fg"],
                     font=("Consolas", 9)).pack()

            tk.Label(wf,
                     text="(tkinterweb dezactivat — folositi butonul pentru browser extern)",
                     bg=TH["bg"], fg="#666666",
                     font=("Consolas", 8)).pack(pady=(8,0))

        # Bind tab selectat -> deschide browser automat
        self._nb.bind("<<NotebookTabChanged>>", self._on_tab_change)
        self._web_lbl = None

        # Tab 3: Cautare in baza locala
        tab_search = tk.Frame(self._nb, bg=TH["bg"])
        self._nb.add(tab_search, text="  Cautare baza locala  ")

        tk.Label(tab_search, text="Cauta dupa indicativ sau nume:",
                 bg=TH["bg"], fg=TH["fg"], font=fn).pack(anchor="w", padx=8, pady=(8, 2))
        sf2 = tk.Frame(tab_search, bg=TH["bg"]); sf2.pack(fill="x", padx=8, pady=2)
        self._search_e = tk.Entry(sf2, width=24, bg=TH["entry_bg"],
                                  fg=TH["fg"], font=fn, insertbackground=TH["fg"])
        self._search_e.pack(side="left")
        self._search_e.bind("<Return>", lambda e: self._search_live())
        tk.Button(sf2, text="Cauta", command=self._search_live,
                  bg=TH["accent"], fg="white", font=fn).pack(side="left", padx=4)

        cols = ["call", "name", "qth", "county", "class", "expires"]
        self._res_tree = ttk.Treeview(tab_search, columns=cols, show="headings", height=16)
        for c, h, w in zip(cols,
                           ["Indicativ", "Titular", "Localitate", "Judet", "Cls", "Expira"],
                           [100, 200, 120, 100, 40, 90]):
            self._res_tree.heading(c, text=h)
            self._res_tree.column(c, width=w, anchor="w")
        sb2 = ttk.Scrollbar(tab_search, orient="vertical", command=self._res_tree.yview)
        self._res_tree.configure(yscrollcommand=sb2.set)
        self._res_tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=4)
        sb2.pack(side="right", fill="y", padx=(0, 8), pady=4)
        self._res_tree.bind("<Double-1>", self._on_result_dbl)

        # Buton inchidere
        tk.Button(self, text=i18n.t("close"), command=self.destroy,
                  bg=TH["btn_bg"], fg="white", font=fn).pack(pady=6)

    # ── Sursa schimbata ───────────────────────────────────────────────────────

    def _on_source_change(self):
        """Cand se schimba sursa, sterge rezultatele vechi."""
        for lbl in self._info_labels.values():
            lbl.config(text="—")
        self._extra_txt.config(state="normal")
        self._extra_txt.delete("1.0", "end")
        self._extra_txt.config(state="disabled")

    # ── Cautare ───────────────────────────────────────────────────────────────

    def _on_key(self, e=None):
        try:
            entry = self._call_e
            c = entry.get().upper()
            pos = entry.index(tk.INSERT)
            entry.delete(0, tk.END); entry.insert(0, c)
            entry.icursor(min(pos, len(c)))
        except Exception:
            pass

    def _lookup(self):
        call = self._call_e.get().upper().strip()
        if not call: return
        src = self._src_v.get()

        if src == "ANCOM Local (offline)":
            result = local_lookup(call)
            if result:
                self._show_result(result, "")
                self._status.config(
                    text=f"Gasit in baza locala ANCOM ({result.get('source','')})",
                    fg=TH["ok"])
            else:
                self._clear_fields()
                self._status.config(
                    text=f"'{call}' nu a fost gasit in baza locala ANCOM",
                    fg=TH["warn"])
        else:
            self._status.config(text="Se cauta online...", fg=TH["warn"])

            def on_result(data, html):
                self._queue.put(("result", data, html))

            def on_error(err):
                self._queue.put(("error", err))

            api_src = "radioamator.ro" if "radioamator" in src else "QRZ.com"
            self._svc.lookup_async(call, api_src, on_result, on_error)

    def _open_browser(self):
        """Deschide pagina callbook in browser extern (thread separat, nu blocheaza UI)."""
        call = self._call_e.get().upper().strip()
        if not call: return
        src = self._src_v.get()
        url_tmpl = URL_TEMPLATES.get(src, URL_TEMPLATES["QRZ.com"])
        url = url_tmpl.format(call)
        threading.Thread(target=webbrowser.open_new_tab, args=(url,),
                         daemon=True, name="browser-open").start()

    def _search_live(self):
        q = self._search_e.get().upper().strip()
        if not q:
            q = self._call_e.get().upper().strip()
            if q:
                self._search_e.delete(0, "end")
                self._search_e.insert(0, q)
        if len(q) < 2:
            self._status.config(text="Introduceti minim 2 caractere", fg=TH["warn"])
            return
        self._nb.select(2)
        results = local_search(q, limit=100)
        for i in self._res_tree.get_children():
            self._res_tree.delete(i)
        for rec in results:
            self._res_tree.insert("", "end", values=[
                rec.get("call", ""),
                rec.get("name", rec.get("owner", "")),
                rec.get("qth",  rec.get("region", "")),
                rec.get("county", rec.get("type", "")),
                rec.get("class", ""),
                rec.get("expires", ""),
            ])
        self._status.config(
            text=f"{len(results)} rezultate pentru '{q}' in baza locala",
            fg=TH["ok"] if results else TH["warn"])

    def _on_result_dbl(self, e=None):
        sel = self._res_tree.selection()
        if not sel: return
        call = self._res_tree.item(sel[0], "values")[0]
        self._call_e.delete(0, "end")
        self._call_e.insert(0, call)
        self._src_v.set(SOURCES[0])
        self._nb.select(0)
        self._lookup()

    # ── Afisare rezultat ──────────────────────────────────────────────────────

    def _build_fields(self, data: dict):
        for w in self._fields_frame.winfo_children():
            w.destroy()
        self._info_labels = {}
        is_rep = data.get("source") == "ANCOM Repetoare" if data else False
        if is_rep:
            keys = ["call","name","owner","type","tx_freq","rx_freq",
                    "power","emission","region","expires","source"]
        else:
            keys = ["call","name","class","qth","county","email",
                    "expires","dxcc","loc","itu","cq","source"]
        for i, k in enumerate(keys):
            r, c = divmod(i, 2)
            tk.Label(self._fields_frame, text=FIELD_LABELS.get(k, k.upper()) + ":",
                     bg=TH["bg"], fg=TH["fg"],
                     font=("Consolas", 9), width=14, anchor="e"
                     ).grid(row=r, column=c*2, sticky="e", padx=(8,2), pady=2)
            lbl = tk.Label(self._fields_frame, text="—",
                           bg=TH["bg"], fg=TH["gold"],
                           font=("Consolas", 9), anchor="w", width=24)
            lbl.grid(row=r, column=c*2+1, sticky="w", padx=(0,8), pady=2)
            self._info_labels[k] = lbl

    def _show_result(self, data: dict, html: str):
        self._build_fields(data)
        for k, lbl in self._info_labels.items():
            val = data.get(k, "")
            lbl.config(text=val if val else "—")

        # Extra info
        self._extra_txt.config(state="normal")
        self._extra_txt.delete("1.0", "end")

        if data.get("source") == "ANCOM Repetoare":
            lines = []
            if data.get("lat"):  lines.append(f"Latitudine : {data['lat']}")
            if data.get("lon"):  lines.append(f"Longitudine: {data['lon']}")
            if data.get("owner"): lines.append(f"Titular    : {data['owner']}")
            self._extra_txt.insert("end", "\n".join(lines))
        elif data.get("source") == "ANCOM RO" and not data.get("name"):
            self._extra_txt.insert("end",
                "Date personale protejate — operatorul a ales confidentialitate in ANCOM.\n"
                "Indicativul este inregistrat si valid.")
        elif data.get("source") == "QRZ.com":
            lines = []
            for k2, lbl2 in [("name","Titular"),("qth","QTH"),("loc","Grid"),
                             ("dxcc","DXCC"),("cq","Zona CQ"),("itu","Zona ITU")]:
                v = data.get(k2,"")
                if v: lines.append(f"{lbl2:<12}: {v}")
            if lines:
                self._extra_txt.insert("end", "\n".join(lines))
        self._extra_txt.config(state="disabled")

        # Tab Web: incarcam pagina
        call = data.get("call", self._call_e.get().upper().strip())
        src  = self._src_v.get()
        if src in URL_TEMPLATES:
            url = URL_TEMPLATES[src].format(call)
            self._load_web(url, call, src)

        # Mesaj date protejate
        if data.get("source") == "ANCOM RO" and not data.get("name"):
            self._status.config(
                text=f"Gasit in ANCOM | Date personale protejate",
                fg="#888888")

    def _on_tab_change(self, event=None):
        """Cand se selecteaza tab-ul Pagina Web, actualizam doar URL label."""
        try:
            current = self._nb.index(self._nb.select())
        except Exception:
            return
        if current == 1:  # Tab Pagina Web
            call = self._call_e.get().upper().strip()
            if call:
                src = self._src_v.get()
                if src in URL_TEMPLATES:
                    url = URL_TEMPLATES[src].format(call)
                    if hasattr(self, "_web_url_lbl"):
                        try: self._web_url_lbl.config(text=url)
                        except Exception: pass

    def _load_web(self, url: str, call: str, src: str):
        """Actualizeaza URL label in tab-ul Web. Browserul se deschide doar la click buton."""
        if hasattr(self, "_web_url_lbl"):
            try: self._web_url_lbl.config(text=url)
            except Exception: pass

    def _clear_fields(self):
        self._build_fields({})
        for lbl in self._info_labels.values():
            lbl.config(text="—")
        self._extra_txt.config(state="normal")
        self._extra_txt.delete("1.0", "end")
        self._extra_txt.config(state="disabled")

    def _update_local_info(self):
        info = local_info()
        if info["available"]:
            self._status.config(
                text=f"Baza locala ANCOM: {info['callbook']:,} indicative + "
                     f"{info['repeaters']:,} repetoare  (data: {info['date']})",
                fg=TH["fg"])
        else:
            self._status.config(
                text="Baza locala nu este disponibila (callbook_local.json lipsa)",
                fg=TH["warn"])

    # ── Queue processor ───────────────────────────────────────────────────────

    def _process_queue(self):
        try:
            while True:
                item = self._queue.get_nowait()
                if item[0] == "result":
                    _, data, html = item
                    if data.get("_error"):
                        self._status.config(text=f"Eroare: {data['_error']}", fg=TH["err"])
                    elif data.get("_not_found"):
                        self._clear_fields()
                        self._status.config(
                            text="Indicativul nu a fost gasit online",
                            fg=TH["warn"])
                    else:
                        self._show_result(data, html)
                        src = data.get("source") or self._src_v.get() or "online"
                        self._status.config(
                            text=f"Gasit online ({src})",
                            fg=TH["ok"])
                elif item[0] == "error":
                    self._status.config(text=f"Eroare: {item[1]}", fg=TH["err"])
        except queue.Empty:
            pass
        except Exception as e:
            logger.debug("callbook queue error: %s", e)
        try:
            self.after(200, self._process_queue)
        except Exception:
            pass
