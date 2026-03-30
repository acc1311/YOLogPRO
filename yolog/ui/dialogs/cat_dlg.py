# -*- coding: utf-8 -*-
"""ui/dialogs/cat_dlg.py — Dialog configurare CAT"""
import tkinter as tk
from tkinter import ttk, messagebox
from ..theme import TH
from ...hardware.cat_engine import (CAT_PROTOCOLS, CAT_BAUD_DEFAULTS,
                                       CAT_SERIAL_DEFAULTS, CAT_PROTOCOL_GROUPS,
                                       CATEngine)
from ... import i18n

def _rg(d,p,iw,ih):
    try: sw,sh=d.winfo_screenwidth(),d.winfo_screenheight()
    except: sw,sh=1366,768
    w,h=min(iw,int(sw*.92)),min(ih,int(sh*.88))
    try: x=p.winfo_rootx()+(p.winfo_width()-w)//2; y=p.winfo_rooty()+(p.winfo_height()-h)//2
    except: x,y=(sw-w)//2,(sh-h)//2
    d.geometry(f"{w}x{h}+{max(0,x)}+{max(0,y)}")

class CATDialog(tk.Toplevel):
    def __init__(self, parent, cfg, cat: CATEngine):
        super().__init__(parent)
        self.result=None; self._cfg=dict(cfg); self._cat=cat
        self.title("CAT — Computer Aided Transceiver"); _rg(self,parent,580,500)
        self.configure(bg=TH["bg"]); self.transient(parent); self.grab_set()
        self._build()

    def _build(self):
        fn = ("Consolas", 10)
        lo = {"bg": TH["bg"], "fg": TH["fg"], "font": fn}
        eo = {"bg": TH["entry_bg"], "fg": TH["fg"], "font": fn, "insertbackground": TH["fg"]}

        # ── Notebook cu tab-uri: Serial / Hamlib ──────────────────────────
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=8)

        tab_serial = tk.Frame(nb, bg=TH["bg"])
        tab_hamlib = tk.Frame(nb, bg=TH["bg"])
        nb.add(tab_serial, text="  Serial / COM  ")
        nb.add(tab_hamlib, text="  Hamlib / rigctld  ")

        # ─────── Tab Serial ───────────────────────────────────────────────
        p = tk.Frame(tab_serial, bg=TH["bg"])
        p.pack(fill="both", expand=True, padx=12, pady=8)

        # Protocol
        tk.Label(p, text="Protocol / Radio:", **lo).grid(row=0, column=0, sticky="w", pady=5)
        self._proto_v = tk.StringVar(value=self._cfg.get("cat_protocol", "Yaesu CAT"))
        proto_cb = ttk.Combobox(p, textvariable=self._proto_v, values=CAT_PROTOCOLS,
                                 state="readonly", width=24, font=fn)
        proto_cb.grid(row=0, column=1, columnspan=3, sticky="w", padx=8, pady=5)
        proto_cb.bind("<<ComboboxSelected>>", self._on_proto)

        # Port COM
        tk.Label(p, text="Port COM:", **lo).grid(row=1, column=0, sticky="w", pady=5)
        ports = CATEngine.list_ports() or [""]
        self._port_v = tk.StringVar(value=self._cfg.get("cat_port", ""))
        ttk.Combobox(p, textvariable=self._port_v, values=ports,
                     width=14, font=fn).grid(row=1, column=1, sticky="w", padx=8, pady=5)

        # Baud rate
        tk.Label(p, text="Baud rate:", **lo).grid(row=2, column=0, sticky="w", pady=5)
        self._baud_v = tk.StringVar(value=str(self._cfg.get("cat_baud", 38400)))
        ttk.Combobox(p, textvariable=self._baud_v,
                     values=["1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"],
                     width=10, font=fn).grid(row=2, column=1, sticky="w", padx=8, pady=5)

        # Separator — parametri seriali avansați
        tk.Frame(p, bg=TH.get("accent", "#1a5276"), height=1).grid(
            row=3, column=0, columnspan=4, sticky="ew", pady=6)
        tk.Label(p, text="Parametri seriali:", bg=TH["bg"], fg=TH.get("gold","#f39c12"),
                 font=("Consolas", 9, "bold")).grid(row=4, column=0, columnspan=4, sticky="w", pady=(0,3))

        # Data bits
        tk.Label(p, text="Data bits:", **lo).grid(row=5, column=0, sticky="w", pady=3)
        self._dbits_v = tk.StringVar(value=str(self._cfg.get("cat_databits", 8)))
        ttk.Combobox(p, textvariable=self._dbits_v, values=["7", "8"],
                     state="readonly", width=5, font=fn).grid(row=5, column=1, sticky="w", padx=8)

        # Parity
        tk.Label(p, text="Paritate:", **lo).grid(row=5, column=2, sticky="w", padx=(12,0))
        self._parity_v = tk.StringVar(value=self._cfg.get("cat_parity", "N"))
        ttk.Combobox(p, textvariable=self._parity_v,
                     values=["N – None", "E – Even", "O – Odd"],
                     state="readonly", width=12, font=fn).grid(row=5, column=3, sticky="w", padx=4)

        # Stop bits
        tk.Label(p, text="Stop bits:", **lo).grid(row=6, column=0, sticky="w", pady=3)
        self._sbits_v = tk.StringVar(value=str(self._cfg.get("cat_stopbits", 2)))
        ttk.Combobox(p, textvariable=self._sbits_v, values=["1", "1.5", "2"],
                     state="readonly", width=5, font=fn).grid(row=6, column=1, sticky="w", padx=8)

        # CI-V Address
        tk.Label(p, text="CI-V Addr (hex):", **lo).grid(row=7, column=0, sticky="w", pady=5)
        self._civ_e = tk.Entry(p, width=8, **eo)
        self._civ_e.insert(0, self._cfg.get("cat_civaddr", "94"))
        self._civ_e.grid(row=7, column=1, sticky="w", padx=8, pady=5)
        tk.Label(p, text="(doar Icom CI-V)", bg=TH["bg"], fg=TH["fg"],
                 font=("Consolas", 8)).grid(row=7, column=2, columnspan=2, sticky="w")

        # ─────── Tab Hamlib ───────────────────────────────────────────────
        h = tk.Frame(tab_hamlib, bg=TH["bg"])
        h.pack(fill="both", expand=True, padx=12, pady=8)

        tk.Label(h, text="Hamlib host:", **lo).grid(row=0, column=0, sticky="w", pady=6)
        self._hhost_e = tk.Entry(h, width=20, **eo)
        self._hhost_e.insert(0, self._cfg.get("cat_hamlib_host", "localhost"))
        self._hhost_e.grid(row=0, column=1, sticky="w", padx=8, pady=6)

        tk.Label(h, text="Hamlib port:", **lo).grid(row=1, column=0, sticky="w", pady=6)
        self._hport_e = tk.Entry(h, width=8, **eo)
        self._hport_e.insert(0, str(self._cfg.get("cat_hamlib_port", 4532)))
        self._hport_e.grid(row=1, column=1, sticky="w", padx=8, pady=6)

        tk.Frame(h, bg=TH.get("accent","#1a5276"), height=1).grid(
            row=2, column=0, columnspan=2, sticky="ew", pady=10)
        info = ("rigctld se pornește separat:\n"
                "  rigctld -m MODEL -r /dev/ttyUSB0 -s 9600\n"
                "  rigctld -m 351 -r COM3 -s 4800   (FT-847)\n"
                "  rigctld -m 3   (FT-817 / FT-897)")
        tk.Label(h, text=info, bg=TH["bg"], fg=TH.get("gold","#f39c12"),
                 font=("Consolas", 9), justify="left", anchor="w").grid(
            row=3, column=0, columnspan=2, sticky="w", padx=4)

        # Switch notebook tab if Hamlib protocol selected
        if self._cfg.get("cat_protocol") == "Hamlib/rigctld":
            nb.select(tab_hamlib)
        proto_cb.bind("<<ComboboxSelected>>",
                      lambda e, n=nb, ts=tab_serial, th=tab_hamlib: (
                          self._on_proto(e),
                          n.select(th if self._proto_v.get() == "Hamlib/rigctld" else ts)
                      ))

        # ── Status + butoane ──────────────────────────────────────────────
        self._status_lbl = tk.Label(self, text="", bg=TH["bg"], fg=TH["ok"], font=fn,
                                    wraplength=480, justify="center")
        self._status_lbl.pack(pady=(4, 2))

        bf = tk.Frame(self, bg=TH["bg"])
        bf.pack(pady=6)
        tk.Button(bf, text="▶ Conectează", command=self._connect,
                  bg=TH["ok"], fg="white", font=fn).pack(side="left", padx=4)
        tk.Button(bf, text="■ Deconectează", command=self._disconnect,
                  bg=TH["err"], fg="white", font=fn).pack(side="left", padx=4)
        tk.Button(bf, text=i18n.t("save"), command=self._save,
                  bg=TH["accent"], fg="white", font=fn).pack(side="left", padx=4)
        tk.Button(bf, text=i18n.t("cancel"), command=self.destroy,
                  bg=TH["btn_bg"], fg="white", font=fn).pack(side="left", padx=4)

    def _on_proto(self, e=None):
        proto = self._proto_v.get()
        baud = CAT_BAUD_DEFAULTS.get(proto, 9600)
        self._baud_v.set(str(baud))
        # Update serial defaults
        defaults = CAT_SERIAL_DEFAULTS.get(proto, (8, "N", 2))
        self._dbits_v.set(str(defaults[0]))
        parity_map = {"N": "N – None", "E": "E – Even", "O": "O – Odd"}
        self._parity_v.set(parity_map.get(defaults[1], "N – None"))
        self._sbits_v.set(str(defaults[2]))

    def _connect(self):
        cfg = self._collect()
        ok, msg = self._cat.connect(cfg)
        self._status_lbl.config(text=msg, fg=TH["ok"] if ok else TH["err"])

    def _disconnect(self):
        self._cat.disconnect()
        self._status_lbl.config(text="Deconectat", fg=TH["warn"])

    def _collect(self):
        # Normalize parity (strip description)
        parity_raw = self._parity_v.get()[:1].upper() if hasattr(self, "_parity_v") else "N"
        return {
            **self._cfg,
            "cat_protocol":    self._proto_v.get(),
            "cat_port":        self._port_v.get(),
            "cat_baud":        int(self._baud_v.get() or 9600),
            "cat_databits":    int(self._dbits_v.get() or 8),
            "cat_parity":      parity_raw,
            "cat_stopbits":    float(self._sbits_v.get() or 2),
            "cat_civaddr":     self._civ_e.get().strip(),
            "cat_hamlib_host": self._hhost_e.get().strip(),
            "cat_hamlib_port": int(self._hport_e.get() or 4532),
        }

    def _save(self):
        self.result = self._collect()
        self.destroy()
