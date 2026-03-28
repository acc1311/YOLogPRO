# -*- coding: utf-8 -*-
"""
tests/test_score.py — Teste pytest pentru core/score.py
Rulare: pytest tests/ -v

Nu necesită Tkinter, serial, sau conexiune de rețea.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from yolog.core.score import Score
from yolog.core.dxcc import DXCC


# ─── Fixture-uri ─────────────────────────────────────────────────────────────

RULES_SIMPLE = {
    "scoring_mode": "none",
    "multiplier_type": "none",
    "points_per_qso": 0,
    "county_list": [],
    "special_scoring": {},
    "allowed_bands": [],
    "allowed_modes": [],
    "required_stations": [],
    "min_qso": 0,
}

RULES_PER_QSO = {
    **RULES_SIMPLE,
    "scoring_mode": "per_qso",
    "points_per_qso": 3,
}

RULES_PER_BAND = {
    **RULES_SIMPLE,
    "scoring_mode": "per_band",
    "band_points": {"40m": 2, "20m": 1, "80m": 3},
    "points_per_qso": 1,
}

RULES_MARATON = {
    **RULES_SIMPLE,
    "scoring_mode": "maraton",
    "multiplier_type": "county",
    "county_list": ["NT", "IS", "SV", "BC", "BT", "VS"],
    "use_county": True,
}

RULES_DISTANCE = {
    **RULES_SIMPLE,
    "scoring_mode": "distance",
    "points_per_qso": 1,
}

CFG_YO8ACR = {"call": "YO8ACR", "loc": "KN37"}


def make_qso(call="YO8ACR", band="40m", mode="SSB", note="", ss="", sr=""):
    return {"c": call, "b": band, "m": mode, "n": note,
            "s": "59", "r": "59", "d": "2024-01-01", "t": "12:00",
            "f": "7100", "ss": ss, "sr": sr}


# ─── Test: punctaj QSO ────────────────────────────────────────────────────────

def test_score_none_returns_zero():
    q = make_qso()
    assert Score.qso(q, RULES_SIMPLE) == 0


def test_score_per_qso():
    q = make_qso()
    assert Score.qso(q, RULES_PER_QSO) == 3


def test_score_per_band_40m():
    q = make_qso(band="40m")
    assert Score.qso(q, RULES_PER_BAND) == 2


def test_score_per_band_80m():
    q = make_qso(band="80m")
    assert Score.qso(q, RULES_PER_BAND) == 3


def test_score_per_band_default():
    q = make_qso(band="15m")  # nu e în band_points
    assert Score.qso(q, RULES_PER_BAND) == 1


def test_score_special_station():
    rules = {**RULES_PER_QSO, "special_scoring": {"YO8ACR": "10"}}
    q = make_qso(call="YO8ACR")
    assert Score.qso(q, rules) == 10


def test_score_distance():
    # KN46 → KN37  150km, deci cel puțin 1 punct
    q = make_qso(note="KN46")
    pts = Score.qso(q, RULES_DISTANCE, CFG_YO8ACR)
    assert pts >= 1


def test_score_distance_invalid_loc():
    q = make_qso(note="INVALID")
    pts = Score.qso(q, RULES_DISTANCE, CFG_YO8ACR)
    assert pts == 1  # fallback la points_per_qso


# ─── Test: duplicate ─────────────────────────────────────────────────────────

def test_is_dup_empty_log():
    assert Score.is_dup([], "YO8ACR", "40m", "SSB") == (False, -1)


def test_is_dup_found():
    log = [make_qso("YO8ACR", "40m", "SSB")]
    is_dup, idx = Score.is_dup(log, "YO8ACR", "40m", "SSB")
    assert is_dup is True
    assert idx == 0


def test_is_dup_different_band():
    log = [make_qso("YO8ACR", "40m", "SSB")]
    is_dup, _ = Score.is_dup(log, "YO8ACR", "20m", "SSB")
    assert is_dup is False


def test_is_dup_different_mode():
    log = [make_qso("YO8ACR", "40m", "SSB")]
    is_dup, _ = Score.is_dup(log, "YO8ACR", "40m", "CW")
    assert is_dup is False


def test_is_dup_case_insensitive():
    log = [make_qso("yo8acr", "40m", "SSB")]
    is_dup, _ = Score.is_dup(log, "YO8ACR", "40m", "SSB")
    assert is_dup is True


def test_is_dup_edit_skip():
    log = [make_qso("YO8ACR", "40m", "SSB")]
    # La editare index 0, nu se consideră dup cu sine
    is_dup, _ = Score.is_dup(log, "YO8ACR", "40m", "SSB", edit_idx=0)
    assert is_dup is False


# ─── Test: multiplicatori ────────────────────────────────────────────────────

def test_mults_none():
    log = [make_qso()]
    count, mset = Score.mults(log, RULES_SIMPLE)
    assert count == 1
    assert mset == set()


def test_mults_county():
    log = [
        make_qso(note="NT"),
        make_qso(note="IS"),
        make_qso(note="NT"),  # duplicat județ
    ]
    count, mset = Score.mults(log, RULES_MARATON)
    assert count == 2
    assert "NT" in mset
    assert "IS" in mset


def test_mults_dxcc():
    rules = {**RULES_SIMPLE, "multiplier_type": "dxcc"}
    log = [
        make_qso("YO8ACR"),
        make_qso("DL1ABC"),
        make_qso("DL2XYZ"),  # același prefix DL
        make_qso("G3ABC"),
    ]
    count, mset = Score.mults(log, rules)
    assert count == 3  # YO, DL, G


# ─── Test: total score ────────────────────────────────────────────────────────

def test_total_empty_log():
    assert Score.total([], RULES_PER_QSO) == (0, 0, 0)


def test_total_per_qso_no_mults():
    log = [make_qso(), make_qso("DL1ABC")]
    qp, mc, tot = Score.total(log, RULES_PER_QSO)
    assert qp == 6   # 2 QSO × 3 puncte
    assert tot == 6  # fără multiplicatori


def test_total_with_county_mults():
    rules = {**RULES_PER_QSO, "multiplier_type": "county",
             "county_list": ["NT", "IS"]}
    log = [
        make_qso(note="NT"),
        make_qso(note="IS"),
    ]
    qp, mc, tot = Score.total(log, rules)
    assert qp == 6
    assert mc == 2
    assert tot == 12  # 6 × 2


# ─── Test: validare ──────────────────────────────────────────────────────────

def test_validate_empty_log():
    ok, msg, score = Score.validate([], RULES_SIMPLE)
    assert ok is False
    assert "gol" in msg.lower() or "empty" in msg.lower()


def test_validate_ok():
    log = [make_qso("YO8ACR"), make_qso("DL1ABC")]
    ok, msg, _ = Score.validate(log, RULES_SIMPLE)
    assert ok is True


def test_validate_min_qso_fail():
    rules = {**RULES_SIMPLE, "min_qso": 5}
    log = [make_qso()]
    ok, msg, _ = Score.validate(log, rules)
    assert ok is False
    assert "5" in msg


def test_validate_required_station_missing():
    rules = {**RULES_SIMPLE, "required_stations": ["YO8ACR"]}
    log = [make_qso("DL1ABC")]
    ok, msg, _ = Score.validate(log, rules)
    assert ok is False
    assert "YO8ACR" in msg


def test_validate_duplicate_detected():
    log = [make_qso("YO8ACR"), make_qso("YO8ACR")]
    ok, msg, _ = Score.validate(log, RULES_SIMPLE)
    assert ok is False
    assert "duplicat" in msg.lower() or "duplicate" in msg.lower()


# ─── Test: DXCC lookup ───────────────────────────────────────────────────────

def test_dxcc_yo():
    country, prefix = DXCC.lookup("YO8ACR")
    assert country == "Romania"
    assert prefix == "YO"


def test_dxcc_dl():
    country, _ = DXCC.lookup("DL1ABC")
    assert country == "Germany"


def test_dxcc_unknown():
    country, _ = DXCC.lookup("ZZ9ZZZ")
    assert country == "Unknown"


def test_dxcc_portable():
    # YO8ACR/P → YO8ACR → YO
    country, _ = DXCC.lookup("YO8ACR/P")
    assert country == "Romania"


# ─── Test: worked_other ──────────────────────────────────────────────────────

def test_worked_other_true():
    log = [make_qso("YO8ACR", "40m", "SSB")]
    assert Score.worked_other(log, "YO8ACR", "20m", "SSB") is True


def test_worked_other_false():
    log = [make_qso("YO8ACR", "40m", "SSB")]
    assert Score.worked_other(log, "YO8ACR", "40m", "SSB") is False


def test_worked_other_not_in_log():
    log = [make_qso("DL1ABC")]
    assert Score.worked_other(log, "YO8ACR", "40m", "SSB") is False

# ─── Test v19: new helpers ───────────────────────────────────────────────────

def test_band_summary():
    log = [make_qso(band="40m"), make_qso(band="20m"), make_qso(band="40m")]
    s = Score.band_summary(log)
    assert s["40m"] == 2
    assert s["20m"] == 1


def test_mode_summary():
    log = [make_qso(mode="SSB"), make_qso(mode="CW"), make_qso(mode="SSB")]
    s = Score.mode_summary(log)
    assert s["SSB"] == 2
    assert s["CW"] == 1


def test_unique_calls():
    log = [make_qso("YO8ACR"), make_qso("DL1ABC"), make_qso("YO8ACR")]
    assert Score.unique_calls(log) == 2


def test_score_none_guards():
    """Test that None values in rules don't crash score calculation."""
    rules_with_none = {
        "scoring_mode": "per_qso",
        "points_per_qso": 1,
        "multiplier_type": "none",
        "special_scoring": None,   # explicit None
        "county_list": None,       # explicit None
        "band_points": None,
        "allowed_bands": [],
        "allowed_modes": [],
        "required_stations": [],
        "min_qso": 0,
    }
    q = make_qso()
    pts = Score.qso(q, rules_with_none)
    assert pts == 1

    count, mset = Score.mults([q], rules_with_none)
    assert count == 1
