# -*- coding: utf-8 -*-
"""
network/local_callbook.py — Baza de date locala ANCOM
Surse: Callbook_16_03_2026.xlsx + Callbook_repetoare_16_03_2026.xlsx

Functioneaza OFFLINE — nu necesita conexiune la internet.
Actualizare: inlocuiti callbook_local.json cu un fisier nou generat
             cu scripts/update_local_callbook.py

Compatible cu PyInstaller: foloseste _MEIPASS pentru a gasi JSON-ul in EXE.
"""
from __future__ import annotations
import json
import os
import sys
import re
import logging

logger = logging.getLogger(__name__)


def _json_path() -> str:
    """Returneaza calea spre callbook_local.json.
    Functioneaza din surse Python si din EXE PyInstaller.
    """
    if getattr(sys, "frozen", False):
        # In EXE: fisierul e la _MEIPASS/yolog/network/callbook_local.json
        return os.path.join(sys._MEIPASS, "yolog", "network", "callbook_local.json")  # type: ignore
    return os.path.join(os.path.dirname(__file__), "callbook_local.json")


# Cache in memorie — incarcat o singura data la primul lookup
_DB: dict | None = None


def _load() -> dict:
    """Incarca JSON-ul in memorie daca nu e deja incarcat."""
    global _DB
    if _DB is not None:
        return _DB
    path = _json_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            _DB = json.load(f)
        n_cb  = len(_DB.get("callbook",  {}))
        n_rep = len(_DB.get("repeaters", {}))
        date  = _DB.get("date", "?")
        logger.info(
            "Callbook local incarcat: %d indicative + %d repetoare (data: %s)",
            n_cb, n_rep, date,
        )
    except FileNotFoundError:
        logger.warning("callbook_local.json nu exista la: %s", path)
        _DB = {"callbook": {}, "repeaters": {}, "date": "?"}
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Eroare citire callbook_local.json: %s", e)
        _DB = {"callbook": {}, "repeaters": {}, "date": "?"}
    return _DB


def _normalize(call: str) -> str:
    """Normalizeaza indicativul pentru lookup: 'yo8acr/p' -> 'YO8ACR'."""
    return re.sub(r'[^A-Z0-9]', '', call.upper().split('/')[0])


def lookup(call: str) -> dict | None:
    """
    Cauta un indicativ in baza locala.
    Returneaza dict cu datele statiei sau None daca nu e gasit.

    Campuri returnate pentru statii:
        call, name, class, qth, county, email, expires, source

    Campuri returnate pentru repetoare:
        call, name, owner, type, tx_freq, rx_freq, power,
        emission, region, lat, lon, expires, source
    """
    db   = _load()
    norm = _normalize(call)

    # 1. Cautare exacta in callbook
    result = db["callbook"].get(norm)
    if result:
        return dict(result)

    # 2. Cautare in repetoare
    result = db["repeaters"].get(norm)
    if result:
        return dict(result)

    # 3. Cautare fuzzy in repetoare (ignoram liniute/underscore)
    norm_stripped = re.sub(r'[-_]', '', norm)
    for key, val in db["repeaters"].items():
        if re.sub(r'[-_]', '', key) == norm_stripped:
            return dict(val)

    return None


def search(query: str, limit: int = 50) -> list[dict]:
    """
    Cauta toate intrarile care contin query in indicativ sau nume.
    Returneaza max `limit` rezultate, sortate: indicative mai intai.
    """
    db    = _load()
    query = query.upper().strip()
    if not query or len(query) < 2:
        return []

    results: list[dict] = []

    for call, rec in db["callbook"].items():
        if query in call or query in rec.get("name", "").upper():
            results.append(dict(rec))
            if len(results) >= limit * 2:
                break

    if len(results) < limit:
        for call, rec in db["repeaters"].items():
            if (query in call
                    or query in rec.get("name", "").upper()
                    or query in rec.get("owner", "").upper()):
                results.append(dict(rec))
                if len(results) >= limit * 2:
                    break

    results.sort(key=lambda r: (0 if r["call"].startswith(query) else 1, r["call"]))
    return results[:limit]


def get_info() -> dict:
    """Returneaza informatii despre baza de date locala."""
    path = _json_path()
    db = _load()
    return {
        "date":       db.get("date", "?"),
        "callbook":   len(db.get("callbook",  {})),
        "repeaters":  len(db.get("repeaters", {})),
        "json_path":  path,
        "available":  os.path.exists(path),
    }


def reload() -> dict:
    """Forteaza reincarcarea JSON-ului (dupa actualizare)."""
    global _DB
    _DB = None
    _load()
    return get_info()
