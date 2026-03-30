# -*- coding: utf-8 -*-
"""
network/callbook_updater.py
Parsare fisiere XLSX ANCOM pentru actualizare callbook local.
Importat de ui/dialogs/update_callbook_dlg.py si scripts/update_local_callbook.py
"""
from __future__ import annotations
import re, datetime

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


def clean(v) -> str:
    v = str(v).strip()
    return "" if v in ("nan", "NaN", "-", "DATE PERSONALE", "None") else v


def parse_callbook(path: str) -> dict:
    if not HAS_PANDAS:
        raise ImportError("pandas nu este instalat. pip install pandas openpyxl")
    import pandas as pd
    df = pd.read_excel(path)
    records = {}
    for _, row in df.iterrows():
        call = clean(row.get("INDICATIVUL", "")).upper()
        if not call:
            continue
        records[call] = {
            "call":    call,
            "name":    clean(row.get("TITULARUL",  "")),
            "class":   clean(str(row.get("CLASA", ""))),
            "qth":     clean(row.get("LOCALITATEA", "")),
            "county":  clean(row.get("JUDETUL",    "")),
            "email":   clean(row.get("E-MAIL",     "")),
            "expires": clean(str(row.get("DATA EXPIRARII", ""))[:10]),
            "source":  "ANCOM RO",
        }
    return records


def parse_repeaters(path: str) -> dict:
    if not HAS_PANDAS:
        raise ImportError("pandas nu este instalat. pip install pandas openpyxl")
    import pandas as pd
    df = pd.read_excel(path)
    records = {}
    for _, row in df.iterrows():
        raw = clean(row.get("Indicativ statie", ""))
        if not raw:
            continue
        call = re.sub(r"^(REPETOR|RADIOBALIZA|SPEC|COORD)\s*", "",
                      raw, flags=re.IGNORECASE).strip().upper()
        if not call:
            call = raw.upper()
        records[call] = {
            "call":     call,
            "name":     clean(row.get("Nume statie",           "")),
            "owner":    clean(row.get("Titular",               "")),
            "type":     clean(row.get("Tip statie",            "")),
            "tx_freq":  clean(row.get("Frecventa de emisie",   "")),
            "rx_freq":  clean(row.get("Frecventa de receptie", "")),
            "power":    clean(row.get("Putere aparent radiata","")),
            "emission": clean(row.get("Simbolul emisiunii",    "")),
            "region":   clean(row.get("Directia Regionala",    "")),
            "lat":      clean(row.get("Latitudine",            "")),
            "lon":      clean(row.get("Longitudine",           "")),
            "expires":  clean(str(row.get("Data expirarii",    ""))[:10]),
            "source":   "ANCOM Repetoare",
        }
    return records
