# -*- coding: utf-8 -*-
"""ui/dialogs/cat_dlg.py — Dialog configurare CAT cu selector modele Hamlib si Test live"""
import tkinter as tk
from tkinter import ttk
from ..theme import TH
from ...hardware.cat_engine import (CAT_PROTOCOLS, CAT_BAUD_DEFAULTS,
                                       CAT_SERIAL_DEFAULTS, CATEngine)
from ... import i18n

def _rg(d, p, iw, ih):
    try: sw, sh = d.winfo_screenwidth(), d.winfo_screenheight()
    except: sw, sh = 1366, 768
    w, h = min(iw, int(sw*.94)), min(ih, int(sh*.92))
    try: x = p.winfo_rootx()+(p.winfo_width()-w)//2; y = p.winfo_rooty()+(p.winfo_height()-h)//2
    except: x, y = (sw-w)//2, (sh-h)//2
    d.geometry(f"{w}x{h}+{max(0,x)}+{max(0,y)}")

# Format: { brand: [(model_id, "NumeAfisat", "nota"), ...] }
HAMLIB_MODELS = {
    "Virtual / Retea": [
        (1,  "DUMMY - Simulator",       "test fara radio"),
        (2,  "NET rigctl - Retea",       "control prin retea"),
        (4,  "FLRig",                    "via FlRig server"),
        (5,  "TRX-Manager",              "via TRX-Manager"),
        (7,  "TCI 1.x - SDR Console",   "SDR prin TCI"),
        (8,  "ACLog",                    "via ACLog"),
        (11, "GQRX",                     "SDR GQRX"),
    ],
    "Icom": [
        (3019, "IC-735",       "CI-V 0x04, 1200 baud"),
        (3020, "IC-736",       "CI-V 0x40"),
        (3021, "IC-737",       "CI-V 0x3C"),
        (3022, "IC-738",       "CI-V 0x44"),
        (3018, "IC-731",       "CI-V 0x02"),
        (3017, "IC-729",       "CI-V 0x3A"),
        (3016, "IC-728",       "CI-V 0x38"),
        (3015, "IC-726",       "CI-V 0x30"),
        (3014, "IC-725",       "CI-V 0x28"),
        (3013, "IC-718",       "CI-V 0x5E"),
        (3012, "IC-707",       "CI-V 0x3E"),
        (3011, "IC-706 MkIIG", "CI-V 0x58"),
        (3010, "IC-706 MkII",  "CI-V 0x4E"),
        (3009, "IC-706",       "CI-V 0x48"),
        (3055, "IC-703",       "CI-V 0x68"),
        (3023, "IC-746",       "CI-V 0x56"),
        (3046, "IC-746 PRO",   "CI-V 0x66"),
        (3026, "IC-756",       "CI-V 0x50"),
        (3027, "IC-756 PRO",   "CI-V 0x5C"),
        (3047, "IC-756 PRO II","CI-V 0x64"),
        (3057, "IC-756 PRO III","CI-V 0x6E"),
        (3056, "IC-7800",      "CI-V 0x6A"),
        (3060, "IC-7000",      "CI-V 0x70"),
        (3061, "IC-7200",      "CI-V 0x76"),
        (3067, "IC-7410",      "CI-V 0x80"),
        (3068, "IC-9100",      "CI-V 0x7C"),
        (3063, "IC-7600",      "CI-V 0x7A"),
        (3062, "IC-7700",      "CI-V 0x74"),
        (3070, "IC-7100",      "CI-V 0x88"),
        (3073, "IC-7300",      "CI-V 0x94"),
        (3094, "IC-7300 MK2",  "CI-V 0xB4"),
        (3078, "IC-7610",      "CI-V 0x98"),
        (3081, "IC-9700",      "CI-V 0xA2"),
        (3085, "IC-705",       "CI-V 0xA4"),
        (3090, "IC-905",       "CI-V 0xAC"),
        (3092, "IC-7760",      "CI-V 0xB2"),
        (3044, "IC-910",       "CI-V 0x60"),
        (3045, "IC-78",        "CI-V 0x62"),
        (3024, "IC-751A",      "CI-V 0x1C"),
        (3028, "IC-761",       "CI-V 0x1E"),
        (3029, "IC-765",       "CI-V 0x2C"),
        (3030, "IC-775",       "CI-V 0x46"),
        (3031, "IC-781",       "CI-V 0x26"),
        (3076, "Xiegu X108G",  "CI-V 0x70"),
        (3087, "Xiegu X6100",  "CI-V 0x70"),
        (3088, "Xiegu G90",    "CI-V 0x70"),
        (3089, "Xiegu X5105",  "CI-V 0x70"),
        (3091, "Xiegu X6200",  "CI-V 0x70"),
    ],
    "Yaesu": [
        (1001, "FT-847",       "4800 baud, 8N2"),
        (1020, "FT-817",       "38400 baud, 8N2"),
        (1041, "FT-818",       "38400 baud, 8N2"),
        (1022, "FT-857",       "38400 baud, 8N2"),
        (1023, "FT-897",       "38400 baud, 8N2"),
        (1043, "FT-897D",      "38400 baud, 8N2"),
        (1021, "FT-100",       "4800 baud, 8N2"),
        (1035, "FT-991",       "38400 baud, 8N2"),
        (1036, "FT-891",       "38400 baud, 8N2"),
        (1049, "FT-710",       "38400 baud, 8N2"),
        (1027, "FT-450",       "38400 baud, 8N2"),
        (1046, "FT-450D",      "38400 baud, 8N2"),
        (1028, "FT-950",       "38400 baud, 8N2"),
        (1029, "FT-2000",      "38400 baud, 8N2"),
        (1032, "FTDX-5000",    "38400 baud, 8N2"),
        (1034, "FTDX-1200",    "38400 baud, 8N2"),
        (1037, "FTDX-3000",    "38400 baud, 8N2"),
        (1040, "FTDX-101D",    "38400 baud, 8N2"),
        (1044, "FTDX-101MP",   "38400 baud, 8N2"),
        (1042, "FTDX-10",      "38400 baud, 8N2"),
        (1030, "FT-9000",      "38400 baud, 8N2"),
        (1010, "FT-736R",      "4800 baud"),
        (1005, "FT-747GX",     "4800 baud"),
        (1006, "FT-757GX",     "4800 baud"),
        (1002, "FT-1000",      "4800 baud"),
        (1003, "FT-1000D",     "4800 baud"),
        (1016, "FT-990",       "4800 baud"),
        (1031, "FT-980",       "4800 baud"),
        (1047, "FT-650",       "4800 baud"),
        (1033, "VX-1700",      "4800 baud"),
    ],
    "Kenwood": [
        (2031, "TS-590S",      "9600 baud, 8N1"),
        (2037, "TS-590SG",     "9600 baud, 8N1"),
        (2028, "TS-480",       "9600 baud, 8N1"),
        (2014, "TS-2000",      "9600 baud, 8N1"),
        (2039, "TS-990S",      "9600 baud, 8N1"),
        (2041, "TS-890S",      "9600 baud, 8N1"),
        (2010, "TS-870S",      "9600 baud, 8N1"),
        (2009, "TS-850",       "9600 baud, 8N1"),
        (2003, "TS-450S",      "9600 baud, 8N1"),
        (2004, "TS-570D",      "9600 baud, 8N1"),
        (2016, "TS-570S",      "9600 baud, 8N1"),
        (2001, "TS-50S",       "9600 baud, 8N1"),
        (2002, "TS-440",       "9600 baud, 8N1"),
        (2005, "TS-690S",      "9600 baud, 8N1"),
        (2007, "TS-790",       "9600 baud, 8N1"),
        (2008, "TS-811",       "9600 baud, 8N1"),
        (2011, "TS-940",       "9600 baud, 8N1"),
        (2012, "TS-950S",      "9600 baud, 8N1"),
        (2022, "TS-930",       "9600 baud, 8N1"),
        (2024, "TS-680S",      "9600 baud, 8N1"),
        (2025, "TS-140S",      "9600 baud, 8N1"),
    ],
    "Elecraft": [
        (2029, "K3",           "38400 baud, 8N2"),
        (2043, "K3S",          "38400 baud, 8N2"),
        (2047, "K4",           "38400 baud, 8N2"),
        (2044, "KX2",          "38400 baud, 8N2"),
        (2045, "KX3",          "38400 baud, 8N2"),
        (2021, "K2",           "4800 baud, 8N2"),
    ],
    "FlexRadio / SDR": [
        (2036, "Flex 6000",    "via Kenwood CAT / SmartSDR"),
        (2048, "PowerSDR",     "FlexRadio legacy"),
        (2040, "OpenHPSDR",    "PiHPSDR / OpenHPSDR"),
        (2051, "SDRuno",       "RSP via SDRuno"),
        (2056, "SDR Console",  "via SDR Console"),
        (2054, "Thetis",       "Apache / Thetis"),
    ],
    "Ten-Tec": [
        (9001, "TT-550 Pegasus", ""),
        (9002, "TT-538 Jupiter", ""),
        (9008, "TT-565 Orion",   ""),
        (9011, "TT-588 Omni-VII",""),
        (9013, "TT-599 Eagle",   ""),
    ],
    "Alinco": [
        (14001, "DX-77",       "9600 baud, 8N1"),
        (14002, "DX-SR8",      "9600 baud, 8N1"),
    ],
    "QRP / Altele": [
        (2052, "QRP Labs QCX", "Kenwood CAT"),
        (2057, "QRP Labs QMX", "Kenwood CAT"),
        (2049, "Malachite",    "SDR portabil"),
        (2055, "truSDX",       "QRP 5W"),
        (2046, "Lab599 TX-500","portabil"),
        (2050, "SDRuno RSP",   "SDRplay RSP"),
        (2053, "FX-4",         "QRP"),
    ],
}


class CATDialog(tk.Toplevel):
    def __init__(self, parent, cfg, cat: CATEngine):
        super().__init__(parent)
        self.result = None
        self._cfg = dict(cfg)
        self._cat = cat
        self.title("CAT - Computer Aided Transceiver")
        _rg(self, parent, 720, 640)
        self.configure(bg=TH["bg"])
        self.transient(parent)
        self.grab_set()
        self._build()

    def _build(self):
        fn  = ("Consolas", 10)
        fns = ("Consolas", 9)
        lo  = {"bg": TH["bg"], "fg": TH["fg"], "font": fn}
        eo  = {"bg": TH["entry_bg"], "fg": TH["fg"], "font": fn,
               "insertbackground": TH["fg"]}

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=8)

        tab_serial = tk.Frame(nb, bg=TH["bg"])
        tab_hamlib = tk.Frame(nb, bg=TH["bg"])
        tab_test   = tk.Frame(nb, bg=TH["bg"])
        nb.add(tab_serial, text="  Serial / COM  ")
        nb.add(tab_hamlib, text="  Hamlib / rigctld  ")
        nb.add(tab_test,   text="  Test CAT  ")

        # ═══ TAB 1 - Serial ════════════════════════════════════════════
        p = tk.Frame(tab_serial, bg=TH["bg"])
        p.pack(fill="both", expand=True, padx=12, pady=8)

        tk.Label(p, text="Protocol / Radio:", **lo).grid(row=0, column=0, sticky="w", pady=5)
        self._proto_v = tk.StringVar(value=self._cfg.get("cat_protocol", "Yaesu CAT"))
        proto_cb = ttk.Combobox(p, textvariable=self._proto_v, values=CAT_PROTOCOLS,
                                 state="readonly", width=24, font=fn)
        proto_cb.grid(row=0, column=1, columnspan=3, sticky="w", padx=8, pady=5)
        proto_cb.bind("<<ComboboxSelected>>", self._on_proto)

        tk.Label(p, text="Port COM:", **lo).grid(row=1, column=0, sticky="w", pady=5)
        ports = CATEngine.list_ports() or [""]
        self._port_v = tk.StringVar(value=self._cfg.get("cat_port", ""))
        ttk.Combobox(p, textvariable=self._port_v, values=ports,
                     width=14, font=fn).grid(row=1, column=1, sticky="w", padx=8, pady=5)

        tk.Label(p, text="Baud rate:", **lo).grid(row=2, column=0, sticky="w", pady=5)
        self._baud_v = tk.StringVar(value=str(self._cfg.get("cat_baud", 38400)))
        ttk.Combobox(p, textvariable=self._baud_v,
                     values=["1200","2400","4800","9600","19200","38400","57600","115200"],
                     width=10, font=fn).grid(row=2, column=1, sticky="w", padx=8, pady=5)

        tk.Frame(p, bg=TH.get("accent","#1a5276"), height=1).grid(
            row=3, column=0, columnspan=4, sticky="ew", pady=6)
        tk.Label(p, text="Parametri seriali:", bg=TH["bg"], fg=TH.get("gold","#f39c12"),
                 font=("Consolas",9,"bold")).grid(row=4, column=0, columnspan=4, sticky="w", pady=(0,3))

        tk.Label(p, text="Data bits:", **lo).grid(row=5, column=0, sticky="w", pady=3)
        self._dbits_v = tk.StringVar(value=str(self._cfg.get("cat_databits", 8)))
        ttk.Combobox(p, textvariable=self._dbits_v, values=["7","8"],
                     state="readonly", width=5, font=fn).grid(row=5, column=1, sticky="w", padx=8)

        tk.Label(p, text="Paritate:", **lo).grid(row=5, column=2, sticky="w", padx=(12,0))
        self._parity_v = tk.StringVar(value=self._cfg.get("cat_parity","N"))
        ttk.Combobox(p, textvariable=self._parity_v,
                     values=["N - None","E - Even","O - Odd"],
                     state="readonly", width=12, font=fn).grid(row=5, column=3, sticky="w", padx=4)

        tk.Label(p, text="Stop bits:", **lo).grid(row=6, column=0, sticky="w", pady=3)
        self._sbits_v = tk.StringVar(value=str(self._cfg.get("cat_stopbits", 2)))
        ttk.Combobox(p, textvariable=self._sbits_v, values=["1","1.5","2"],
                     state="readonly", width=5, font=fn).grid(row=6, column=1, sticky="w", padx=8)

        tk.Label(p, text="CI-V Addr (hex):", **lo).grid(row=7, column=0, sticky="w", pady=5)
        self._civ_e = tk.Entry(p, width=6, **eo)
        self._civ_e.insert(0, self._cfg.get("cat_civaddr","94"))
        self._civ_e.grid(row=7, column=1, sticky="w", padx=8, pady=5)
        civ_hint = ("Adrese uzuale Icom:\n"
                    "IC-735=04  IC-746=56  IC-756=50\n"
                    "IC-7000=70  IC-7300=94  IC-7610=98\n"
                    "IC-705=A4  IC-9700=A2  IC-7800=6A")
        tk.Label(p, text=civ_hint, bg=TH["bg"], fg=TH.get("gold","#f39c12"),
                 font=("Consolas",8), justify="left").grid(
            row=7, column=2, columnspan=2, sticky="w", padx=4)

        # ═══ TAB 2 - Hamlib cu selector model ═════════════════════════
        h = tk.Frame(tab_hamlib, bg=TH["bg"])
        h.pack(fill="both", expand=True, padx=12, pady=8)

        tk.Label(h, text="rigctld host:", **lo).grid(row=0, column=0, sticky="w", pady=4)
        self._hhost_e = tk.Entry(h, width=18, **eo)
        self._hhost_e.insert(0, self._cfg.get("cat_hamlib_host","localhost"))
        self._hhost_e.grid(row=0, column=1, sticky="w", padx=8, pady=4)
        tk.Label(h, text="Port:", **lo).grid(row=0, column=2, sticky="w", padx=(8,0))
        self._hport_e = tk.Entry(h, width=7, **eo)
        self._hport_e.insert(0, str(self._cfg.get("cat_hamlib_port",4532)))
        self._hport_e.grid(row=0, column=3, sticky="w", padx=4, pady=4)

        tk.Frame(h, bg=TH.get("accent","#1a5276"), height=1).grid(
            row=1, column=0, columnspan=4, sticky="ew", pady=6)
        tk.Label(h, text="Selecteaza modelul transceiverului:", bg=TH["bg"],
                 fg=TH.get("gold","#f39c12"), font=("Consolas",9,"bold")).grid(
            row=2, column=0, columnspan=4, sticky="w", pady=(0,4))

        brands = list(HAMLIB_MODELS.keys())

        brand_frame = tk.Frame(h, bg=TH["bg"])
        brand_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=(0,4))
        tk.Label(brand_frame, text="Brand:", bg=TH["bg"], fg=TH["fg"], font=fns).pack(anchor="w")
        brand_sb = tk.Scrollbar(brand_frame, orient="vertical")
        self._brand_lb = tk.Listbox(brand_frame, width=22, height=9,
                                     bg=TH["entry_bg"], fg=TH["fg"], font=fns,
                                     selectbackground=TH.get("accent","#1a5276"),
                                     selectforeground="white", bd=0, activestyle="none",
                                     yscrollcommand=brand_sb.set)
        brand_sb.config(command=self._brand_lb.yview)
        self._brand_lb.pack(side="left", fill="both", expand=True)
        brand_sb.pack(side="right", fill="y")
        for b in brands:
            self._brand_lb.insert(tk.END, f" {b}")

        model_frame = tk.Frame(h, bg=TH["bg"])
        model_frame.grid(row=3, column=2, columnspan=2, sticky="nsew")
        tk.Label(model_frame, text="Model (dublu-click = selecteaza):", bg=TH["bg"], fg=TH["fg"], font=fns).pack(anchor="w")
        model_sb = tk.Scrollbar(model_frame, orient="vertical")
        self._model_lb = tk.Listbox(model_frame, width=36, height=9,
                                     bg=TH["entry_bg"], fg=TH["fg"], font=fns,
                                     selectbackground=TH.get("ok","#1e8449"),
                                     selectforeground="white", bd=0, activestyle="none",
                                     yscrollcommand=model_sb.set)
        model_sb.config(command=self._model_lb.yview)
        self._model_lb.pack(side="left", fill="both", expand=True)
        model_sb.pack(side="right", fill="y")

        self._model_note = tk.Label(h, text="", bg=TH["bg"],
                                     fg=TH.get("gold","#f39c12"), font=fns, anchor="w")
        self._model_note.grid(row=4, column=0, columnspan=4, sticky="w", pady=(3,0))

        id_frame = tk.Frame(h, bg=TH["bg"])
        id_frame.grid(row=5, column=0, columnspan=4, sticky="w", pady=5)
        tk.Label(id_frame, text="Model ID rigctld  -m :", **lo).pack(side="left")
        self._model_id_v = tk.StringVar(value=str(self._cfg.get("cat_hamlib_model",3073)))
        self._model_id_e = tk.Entry(id_frame, textvariable=self._model_id_v, width=8, **eo)
        self._model_id_e.pack(side="left", padx=8)
        tk.Label(id_frame, text="(editabil manual pentru orice model)", bg=TH["bg"],
                 fg=TH["fg"], font=fns).pack(side="left")

        self._rigctld_lbl = tk.Label(h, text="", bg=TH["bg"],
                                      fg=TH.get("gold","#f39c12"),
                                      font=("Consolas",8), anchor="w")
        self._rigctld_lbl.grid(row=6, column=0, columnspan=4, sticky="w")

        # Events
        self._brands_list = brands
        self._brand_lb.bind("<<ListboxSelect>>", self._on_brand_select)
        self._model_lb.bind("<<ListboxSelect>>", self._on_model_select)
        self._model_lb.bind("<Double-Button-1>", self._on_model_apply)
        self._model_id_v.trace_add("write", lambda *a: self._update_rigctld_cmd())

        # Select initial brand/model
        default_brand_idx = 1  # Icom
        self._brand_lb.selection_set(default_brand_idx)
        self._fill_models(brands[default_brand_idx])
        self._select_saved_model(brands[default_brand_idx])

        # ═══ TAB 3 - Test CAT live ═════════════════════════════════════
        t = tk.Frame(tab_test, bg=TH["bg"])
        t.pack(fill="both", expand=True, padx=14, pady=10)

        tk.Label(t, text="Test CAT live - citire si scriere frecventa / mod",
                 bg=TH["bg"], fg=TH.get("gold","#f39c12"),
                 font=("Consolas",10,"bold")).grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0,10))

        # Citire
        tk.Label(t, text="Frecventa citita:", **lo).grid(row=1, column=0, sticky="w", pady=4)
        self._read_freq_v = tk.StringVar(value="---")
        tk.Label(t, textvariable=self._read_freq_v, bg=TH["entry_bg"],
                 fg=TH.get("ok","#27ae60"), font=("Consolas",15,"bold"),
                 width=13, anchor="e", relief="sunken", padx=6).grid(
            row=1, column=1, sticky="w", padx=8)
        tk.Label(t, text="kHz", **lo).grid(row=1, column=2, sticky="w")

        tk.Label(t, text="Mod citit:", **lo).grid(row=2, column=0, sticky="w", pady=4)
        self._read_mode_v = tk.StringVar(value="---")
        tk.Label(t, textvariable=self._read_mode_v, bg=TH["entry_bg"],
                 fg=TH.get("ok","#27ae60"), font=("Consolas",13,"bold"),
                 width=8, anchor="center", relief="sunken").grid(
            row=2, column=1, sticky="w", padx=8)

        tk.Button(t, text="Citeste acum", command=self._test_read,
                  bg=TH.get("accent","#1a5276"), fg="white",
                  font=fn, padx=10).grid(row=1, column=3, rowspan=2,
                  padx=12, sticky="ns")

        tk.Frame(t, bg=TH.get("accent","#1a5276"), height=1).grid(
            row=3, column=0, columnspan=4, sticky="ew", pady=10)

        # Scriere frecventa
        tk.Label(t, text="Trimite frecventa:", **lo).grid(row=4, column=0, sticky="w", pady=4)
        self._send_freq_e = tk.Entry(t, width=12, **eo)
        self._send_freq_e.grid(row=4, column=1, sticky="w", padx=8)
        tk.Label(t, text="kHz", **lo).grid(row=4, column=2, sticky="w")
        tk.Button(t, text="Trimite", command=self._test_set_freq,
                  bg=TH.get("ok","#1e8449"), fg="white",
                  font=fn, padx=10).grid(row=4, column=3, padx=12)

        # Scriere mod
        tk.Label(t, text="Trimite mod:", **lo).grid(row=5, column=0, sticky="w", pady=4)
        self._send_mode_v = tk.StringVar(value="USB")
        ttk.Combobox(t, textvariable=self._send_mode_v,
                     values=["LSB","USB","CW","AM","FM","DIGI","RTTY","FT8","FT4"],
                     state="readonly", width=10, font=fn).grid(
            row=5, column=1, sticky="w", padx=8)
        tk.Button(t, text="Trimite", command=self._test_set_mode,
                  bg=TH.get("ok","#1e8449"), fg="white",
                  font=fn, padx=10).grid(row=5, column=3, padx=12)

        tk.Frame(t, bg=TH.get("accent","#1a5276"), height=1).grid(
            row=6, column=0, columnspan=4, sticky="ew", pady=8)

        tk.Label(t, text="Log test:", bg=TH["bg"], fg=TH.get("gold","#f39c12"),
                 font=fns).grid(row=7, column=0, columnspan=4, sticky="w")
        self._test_log = tk.Text(t, height=6, bg=TH["entry_bg"], fg=TH["fg"],
                                  font=("Consolas",9), state="disabled",
                                  relief="sunken", bd=1)
        self._test_log.grid(row=8, column=0, columnspan=4, sticky="ew", pady=(2,0))
        tk.Button(t, text="Goleste log", command=self._clear_log,
                  bg=TH.get("btn_bg","#2c3e50"), fg="white", font=fns).grid(
            row=9, column=3, sticky="e", pady=4)

        # Switch la tab hamlib daca e setat
        if self._cfg.get("cat_protocol") == "Hamlib/rigctld":
            nb.select(tab_hamlib)
        proto_cb.bind("<<ComboboxSelected>>",
                      lambda e, n=nb, ts=tab_serial, th=tab_hamlib: (
                          self._on_proto(e),
                          n.select(th if self._proto_v.get() == "Hamlib/rigctld" else ts)
                      ))

        # Status + butoane
        self._status_lbl = tk.Label(self, text="", bg=TH["bg"], fg=TH.get("ok","#27ae60"),
                                     font=fn, wraplength=580, justify="center")
        self._status_lbl.pack(pady=(4,2))

        bf = tk.Frame(self, bg=TH["bg"])
        bf.pack(pady=6)
        tk.Button(bf, text="Conecteaza", command=self._connect,
                  bg=TH.get("ok","#1e8449"), fg="white", font=fn).pack(side="left", padx=4)
        tk.Button(bf, text="Deconecteaza", command=self._disconnect,
                  bg=TH.get("err","#c0392b"), fg="white", font=fn).pack(side="left", padx=4)
        tk.Button(bf, text=i18n.t("save"), command=self._save,
                  bg=TH.get("accent","#1a5276"), fg="white", font=fn).pack(side="left", padx=4)
        tk.Button(bf, text=i18n.t("cancel"), command=self.destroy,
                  bg=TH.get("btn_bg","#2c3e50"), fg="white", font=fn).pack(side="left", padx=4)

    # ─── Model Hamlib helpers ─────────────────────────────────────────────────

    def _fill_models(self, brand_name):
        self._model_lb.delete(0, tk.END)
        for mid, name, note in HAMLIB_MODELS.get(brand_name, []):
            self._model_lb.insert(tk.END, f"  {mid:6d}   {name}")

    def _select_saved_model(self, brand_name):
        try:
            saved_id = int(self._model_id_v.get())
        except ValueError:
            return
        for i, (mid, name, note) in enumerate(HAMLIB_MODELS.get(brand_name, [])):
            if mid == saved_id:
                self._model_lb.selection_set(i)
                self._model_lb.see(i)
                self._model_note.config(
                    text=f"  {name}  |  {note}" if note else f"  {name}")
                self._update_rigctld_cmd()
                return

    def _on_brand_select(self, e=None):
        sel = self._brand_lb.curselection()
        if sel:
            brand = self._brands_list[sel[0]]
            self._fill_models(brand)
            self._select_saved_model(brand)

    def _on_model_select(self, e=None):
        sel = self._model_lb.curselection()
        if not sel:
            return
        brand_sel = self._brand_lb.curselection()
        if not brand_sel:
            return
        brand = self._brands_list[brand_sel[0]]
        idx = sel[0]
        if idx < len(HAMLIB_MODELS.get(brand, [])):
            mid, name, note = HAMLIB_MODELS[brand][idx]
            self._model_id_v.set(str(mid))
            self._model_note.config(
                text=f"  {name}  |  {note}" if note else f"  {name}")
            self._update_rigctld_cmd()

    def _on_model_apply(self, e=None):
        self._on_model_select()

    def _update_rigctld_cmd(self):
        try:
            mid  = self._model_id_v.get().strip()
            port_val = self._port_v.get() if hasattr(self, "_port_v") else "COM3"
            baud_val = self._baud_v.get() if hasattr(self, "_baud_v") else "9600"
            hport = self._hport_e.get().strip() if hasattr(self, "_hport_e") else "4532"
            cmd = f"rigctld -m {mid} -r {port_val or 'COM3'} -s {baud_val or '9600'} -t {hport}"
            self._rigctld_lbl.config(text=f"  Cmd: {cmd}")
        except Exception:
            pass

    # ─── Test CAT ────────────────────────────────────────────────────────────

    def _log(self, msg):
        self._test_log.config(state="normal")
        self._test_log.insert(tk.END, msg + "\n")
        self._test_log.see(tk.END)
        self._test_log.config(state="disabled")

    def _clear_log(self):
        self._test_log.config(state="normal")
        self._test_log.delete("1.0", tk.END)
        self._test_log.config(state="disabled")

    def _test_read(self):
        if not self._cat.connected:
            self._log("CAT neconectat - apasa Conecteaza mai intai")
            return
        freq = self._cat.last_freq or "?"
        mode = self._cat.last_mode or "?"
        self._read_freq_v.set(freq)
        self._read_mode_v.set(mode)
        self._log(f"OK  Citit: {freq} kHz  |  {mode}")

    def _test_set_freq(self):
        if not self._cat.connected:
            self._log("CAT neconectat")
            return
        khz = self._send_freq_e.get().strip()
        if not khz:
            self._log("Introdu o frecventa in kHz")
            return
        ok = self._cat.set_freq(khz)
        self._log(f"{'OK' if ok else 'ERR'}  Frecventa trimisa: {khz} kHz")

    def _test_set_mode(self):
        if not self._cat.connected:
            self._log("CAT neconectat")
            return
        mode = self._send_mode_v.get()
        ok = self._cat.set_mode(mode)
        self._log(f"{'OK' if ok else 'ERR'}  Mod trimis: {mode}")

    # ─── Protocol helpers ────────────────────────────────────────────────────

    def _on_proto(self, e=None):
        proto = self._proto_v.get()
        baud = CAT_BAUD_DEFAULTS.get(proto, 9600)
        self._baud_v.set(str(baud))
        defaults = CAT_SERIAL_DEFAULTS.get(proto, (8, "N", 2))
        self._dbits_v.set(str(defaults[0]))
        parity_map = {"N": "N - None", "E": "E - Even", "O": "O - Odd"}
        self._parity_v.set(parity_map.get(defaults[1], "N - None"))
        self._sbits_v.set(str(defaults[2]))

    def _connect(self):
        cfg = self._collect()
        ok, msg = self._cat.connect(cfg)
        self._status_lbl.config(
            text=msg, fg=TH.get("ok","#27ae60") if ok else TH.get("err","#e74c3c"))
        self._log(f"{'OK' if ok else 'ERR'}  {msg}")

    def _disconnect(self):
        self._cat.disconnect()
        self._status_lbl.config(text="Deconectat", fg=TH.get("warn","#f39c12"))
        self._log("Deconectat")

    def _collect(self):
        parity_raw = self._parity_v.get()[:1].upper() if hasattr(self, "_parity_v") else "N"
        try:
            hamlib_model = int(self._model_id_v.get().strip())
        except (ValueError, AttributeError):
            hamlib_model = 3073
        return {
            **self._cfg,
            "cat_protocol":     self._proto_v.get(),
            "cat_port":         self._port_v.get(),
            "cat_baud":         int(self._baud_v.get() or 9600),
            "cat_databits":     int(self._dbits_v.get() or 8),
            "cat_parity":       parity_raw,
            "cat_stopbits":     float(self._sbits_v.get() or 2),
            "cat_civaddr":      self._civ_e.get().strip(),
            "cat_hamlib_host":  self._hhost_e.get().strip(),
            "cat_hamlib_port":  int(self._hport_e.get() or 4532),
            "cat_hamlib_model": hamlib_model,
        }

    def _save(self):
        self.result = self._collect()
        self.destroy()
