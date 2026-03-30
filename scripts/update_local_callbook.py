#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/update_local_callbook.py
Regenerează network/callbook_local.json din fișierele XLSX ANCOM.

Utilizare:
    python scripts/update_local_callbook.py \
        --callbook  Callbook_16_03_2026.xlsx \
        --repetoare Callbook_repetoare_16_03_2026.xlsx

Plasați fișierele .xlsx în același director sau specificați calea completă.
Necesită: pip install openpyxl pandas
"""
import argparse
import json
import re
import sys
import os
import datetime

try:
    import pandas as pd
except ImportError:
    print("EROARE: pandas nu este instalat.\n  pip install pandas openpyxl")
    sys.exit(1)


def clean(v) -> str:
    v = str(v).strip()
    return "" if v in ("nan", "NaN", "-", "DATE PERSONALE", "None") else v


def parse_callbook(path: str) -> dict:
    print(f"  Citesc callbook: {path}")
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
    print(f"    → {len(records)} indicative")
    return records


def parse_repeaters(path: str) -> dict:
    print(f"  Citesc repetoare: {path}")
    df = pd.read_excel(path)
    records = {}
    for _, row in df.iterrows():
        raw = clean(row.get("Indicativ statie", ""))
        if not raw:
            continue
        # Extrage indicativul real (scoatem prefix REPETOR / RADIOBALIZA etc.)
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
    print(f"    → {len(records)} repetoare")
    return records


def main():
    parser = argparse.ArgumentParser(description="Generează callbook_local.json din XLSX ANCOM")
    parser.add_argument("--callbook",  required=True, help="Callbook_*.xlsx")
    parser.add_argument("--repetoare", required=True, help="Callbook_repetoare_*.xlsx")
    parser.add_argument("--output",    default=None,  help="Cale ieșire JSON (implicit: network/callbook_local.json)")
    args = parser.parse_args()

    # Locație implicită output: lângă scriptul curent → ../network/
    if args.output is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        args.output = os.path.join(script_dir, "..", "network", "callbook_local.json")

    print("YO Log PRO — Generator Callbook Local")
    print("=" * 40)

    callbook  = parse_callbook(args.callbook)
    repeaters = parse_repeaters(args.repetoare)

    output = {
        "date":      datetime.date.today().isoformat(),
        "callbook":  callbook,
        "repeaters": repeaters,
    }

    out_path = os.path.abspath(args.output)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, separators=(",", ":"))

    size_kb = os.path.getsize(out_path) // 1024
    print(f"\n Salvat: {out_path} ({size_kb} KB)")
    print(f"  Callbook:  {len(callbook):,} indicative")
    print(f"  Repetoare: {len(repeaters):,} intrări")
    print(f"\nPentru actualizare viitoare:")
    print(f"  python scripts/update_local_callbook.py \\")
    print(f"      --callbook  Callbook_NOU.xlsx \\")
    print(f"      --repetoare Callbook_repetoare_NOU.xlsx")


if __name__ == "__main__":
    main()
