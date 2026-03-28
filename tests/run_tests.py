#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/run_tests.py — Script de teste standalone pentru GitHub Actions CI
Rulare: python tests/run_tests.py  (din root-ul repo-ului)
"""
import sys, os
# Adaugam root-ul repo ca pachet 'yolog' pentru a mentine importurile relative
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(repo_root))  # parintele lui repo

# Facem folderul curent sa fie recunoscut ca pachetul 'yolog'
import importlib, types
pkg_name = os.path.basename(repo_root)  # numele folderului = 'yolog' sau alt nume
# Cream un modul virtual cu numele folderului care pointeaza la repo_root
mod = types.ModuleType(pkg_name)
mod.__path__ = [repo_root]
mod.__package__ = pkg_name
mod.__spec__ = importlib.util.spec_from_file_location(pkg_name, os.path.join(repo_root, '__init__.py'))
sys.modules[pkg_name] = mod

errors = []
passed = 0

def t(name, fn):
    global passed
    try:
        fn()
        print(f"    {name}")
        passed += 1
    except Exception as e:
        errors.append(f"{name}: {e}")
        print(f"    {name}: {e}")

# Import-uri cu calea completa dupa ce am setat pachetul
exec_globals = {}
exec(f"""
sys.path.insert(0, r'{repo_root}')
""", {"sys": sys})

import importlib.util

def imp(module_path):
    """Importa un modul din repo root."""
    parts = module_path.split('.')
    full_path = os.path.join(repo_root, *parts) + '.py'
    if not os.path.exists(full_path):
        full_path = os.path.join(repo_root, *parts[:-1], parts[-1]) + '.py'
    spec = importlib.util.spec_from_file_location(module_path, full_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_path] = mod
    spec.loader.exec_module(mod)
    return mod

if __name__ == '__main__':
    print("=== YO Log PRO v19 — Teste CI ===\n")
    print(f"Python: {sys.version}")
    print(f"Root: {repo_root}\n")

    # Rulam testele ca pachet normal
    try:
        # Adaugam parintele ca sa functioneze importurile relative
        parent = os.path.dirname(repo_root)
        if parent not in sys.path:
            sys.path.insert(0, parent)
        
        pkg = os.path.basename(repo_root)
        
        exec(f"from {pkg}.core.score import Score", globals())
        exec(f"from {pkg}.core.dxcc import DXCC", globals())
        exec(f"from {pkg}.core.locator import Loc", globals())
        exec(f"from {pkg}.core.bands import freq2band", globals())
        exec(f"from {pkg}.data.importer import Importer", globals())
        exec(f"from {pkg}.export.exporters import CabrilloExporter, ADIFExporter", globals())
        print("    Importuri module")
    except Exception as e:
        print(f"    Import FAIL: {e}")
        sys.exit(1)

    def chk_dxcc():
        assert DXCC.lookup('YO8ACR')[0] == 'Romania'
        assert DXCC.lookup('DL1ABC')[0] == 'Germany'
        assert DXCC.lookup('ZZ9ZZZ')[0] == 'Unknown'
    t("DXCC lookup", chk_dxcc)

    def chk_bands():
        assert freq2band(14200) == '20m'
        assert freq2band(7100) == '40m'
        assert freq2band(99999) is None
    t("Benzi", chk_bands)

    def chk_score():
        rules = {'scoring_mode':'per_qso','points_per_qso':3,'multiplier_type':'none','special_scoring':{}}
        q = {'c':'YO8ACR','b':'40m','m':'SSB','n':'','s':'59','r':'59','d':'2024-01-01','t':'12:00','f':'7100'}
        assert Score.qso(q, rules) == 3
        assert not Score.is_dup([q], 'DL1ABC', '40m', 'SSB')[0]
    t("Score engine", chk_score)

    def chk_adif():
        q = {'c':'YO8ACR','b':'40m','m':'SSB','n':'KN37','s':'59','r':'59','d':'2024-01-15','t':'12:00','f':'7100','ss':'','sr':''}
        adif = ADIFExporter.export([q], {'call':'YO8ACR','loc':'KN37'})
        ri = Importer.parse_adif(adif)
        assert len(ri) == 1 and ri[0]['c'] == 'YO8ACR'
    t("ADIF round-trip", chk_adif)

    print()
    total = 4
    ok = total - len(errors)
    print(f"{'='*40}")
    print(f"  Rezultat: {ok}/{total} OK")
    if errors:
        for e in errors: print(f"    {e}")
        sys.exit(1)
    else:
        print(f"   Toate testele trecute")
    print(f"{'='*40}")
