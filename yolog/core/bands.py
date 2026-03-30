# -*- coding: utf-8 -*-
"""
core/bands.py — Constante benzi, moduri, frecvente
Zero dependente externe. Import din orice modul.
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

# ─── Mapare frecventa (kHz) → banda ──────────────────────────────────────────
FREQ_MAP: dict[tuple[int, int], str] = {
    (1800,    2000):   "160m",
    (3500,    3800):   "80m",
    (5351,    5367):   "60m",
    (7000,    7200):   "40m",
    (10100,  10150):   "30m",
    (14000,  14350):   "20m",
    (18068,  18168):   "17m",
    (21000,  21450):   "15m",
    (24890,  24990):   "12m",
    (28000,  29700):   "10m",
    (50000,  54000):   "6m",
    (144000, 148000):  "2m",
    (430000, 440000):  "70cm",
    (1240000,1300000): "23cm",
    (2300000,2450000): "13cm",
    (3400000,3410000): "9cm",
    (5650000,5850000): "6cm",
}

# ─── Banda → frecventa centrala tipica (kHz) ─────────────────────────────────
BAND_FREQ: dict[str, int] = {
    "160m": 1850, "80m": 3700, "60m": 5355, "40m": 7100,
    "30m": 10120, "20m": 14200, "17m": 18120, "15m": 21200,
    "12m": 24940, "10m": 28500, "6m": 50150, "2m": 145000,
    "70cm": 432200, "23cm": 1296200, "13cm": 2320000,
    "9cm": 3400000, "6cm": 5760000,
}

# ─── Mod → RST implicit ───────────────────────────────────────────────────────
RST_DEFAULTS: dict[str, str] = {
    "SSB": "59", "AM": "59", "FM": "59", "SSTV": "59",
    "CW": "599", "RTTY": "599", "PSK31": "599", "DIGI": "599",
    "FT8": "-10", "FT4": "-10", "JT65": "-15",
}

# ─── Mapare mod → Cabrillo 2.0 ───────────────────────────────────────────────
CAB2_MODE_MAP: dict[str, str] = {
    "SSB": "PH", "AM": "PH", "FM": "PH", "SSTV": "PH",
    "CW": "CW", "RTTY": "RY", "PSK31": "RY",
    "FT8": "DG", "FT4": "DG", "JT65": "DG", "DIGI": "DG",
}
CAB2_MODE_REV: dict[str, str] = {
    "PH": "SSB", "CW": "CW", "RY": "RTTY", "DG": "FT8",
}

# ─── Liste benzi si moduri ────────────────────────────────────────────────────
BANDS_HF   = ["160m","80m","60m","40m","30m","20m","17m","15m","12m","10m"]
BANDS_VHF  = ["6m", "2m"]
BANDS_UHF  = ["70cm", "23cm", "13cm", "9cm", "6cm"]
BANDS_ALL  = BANDS_HF + BANDS_VHF + BANDS_UHF

MODES_ALL  = ["SSB","CW","DIGI","FT8","FT4","RTTY","AM","FM","PSK31","SSTV","JT65"]

# ─── Tipuri concurs / exchange ────────────────────────────────────────────────
SCORING_MODES    = ["none","per_qso","per_band","maraton","multiplier","distance","custom"]
EXCHANGE_FORMATS = ["none","county","grid","serial","serial_county","zone","custom"]
CONTEST_TYPES    = ["Simplu","Maraton","Stafeta","YO","DX","VHF","UHF","Field Day",
                    "Sprint","QSO Party","SOTA","POTA","Digital","CW","Custom"]

# ─── Judete YO ───────────────────────────────────────────────────────────────
YO_COUNTIES = [
    "AB","AR","AG","BC","BH","BN","BT","BV","BR","BZ","CS","CL","CJ","CT","CV",
    "DB","DJ","GL","GR","GJ","HR","HD","IL","IS","IF","MM","MH","MS","NT","OT",
    "PH","SM","SJ","SB","SV","TR","TM","TL","VS","VL","VN","B",
]


def freq2band(f) -> str | None:
    """
    Converteste frecventa (kHz, int sau float sau str) la banda.
    Returneaza None daca frecventa nu se incadreaza in nicio banda.
    """
    try:
        fv = float(f)
        for (lo, hi), band in FREQ_MAP.items():
            if lo <= fv <= hi:
                return band
    except (ValueError, TypeError) as e:
        logger.debug("freq2band: valoare invalida '%s': %s", f, e)
    return None


def band2freq(band: str) -> int:
    """Returneaza frecventa centrala tipica (kHz) pentru o banda."""
    return BAND_FREQ.get(band, 0)
