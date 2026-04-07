# -*- coding: utf-8 -*-
"""
ui/app.py — Clasa principală App (tk.Tk)
Responsabilități: orchestrare UI, gestionare stare, delegare spre module specializate.
CAT → thread-safe prin queue.Queue + after()
"""
from __future__ import annotations
import queue
import copy
import hashlib
import json
import datetime
import logging
from collections import deque

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext, Menu

from ..core.score import Score
from ..core.dxcc import DXCC
from ..core.bands import (
    BANDS_ALL, BANDS_HF, BANDS_VHF, MODES_ALL,
    RST_DEFAULTS, BAND_FREQ, freq2band,
)
from ..data.manager import DataManager
from ..data.importer import Importer
from ..export.exporters import (
    CabrilloExporter, ADIFExporter, CSVExporter,
    EDIExporter, PrintExporter,
)
from ..hardware.cat_engine import CATEngine
from .. import i18n
from .theme import TH, THEMES, apply_theme, setup_ttk_style, UIFactory
from .dialogs.contest_mgr import ContestMgr, ContestEditor
from .dialogs.settings_dlg import SettingsDialog
from .dialogs.export_dlg import ExportDialog
from .dialogs.timer_dlg import TimerDialog
from .dialogs.search_dlg import SearchDialog
from .dialogs.stats_dlg import StatsDialog
from .dialogs.cat_dlg import CATDialog
from .dialogs.preview_dlg import PreviewDialog
from .dialogs.calendar_popup import CalendarPopup
from .dialogs.firstrun_dlg import FirstRunDialog
from .dialogs.cabrillo_dlg import Cab3ConfigDialog, Cab2ConfigDialog
from .dialogs.newlog_dlg import NewLogDialog
from .dialogs.theme_dlg import ThemeDialog
from .dialogs.log_editor import LogEditorWindow
from .dialogs.band_map import BandMapWindow
from .dialogs.dx_cluster import DXClusterWindow
from .dialogs.rate_stats import RateStatsWindow
from .dialogs.live_score import LiveScorePanel

logger = logging.getLogger(__name__)

# Constante
DEFAULT_CFG = {
    "call": "YO8ACR", "loc": "KN37", "jud": "NT", "addr": "",
    "cat": 0, "fs": 11, "contest": "simplu", "county": "NT",
    "lang": "ro", "manual_dt": False, "sounds": True, "scroll_popups": True,
    "op_name": "", "power": "100", "win_geo": "",
    "email": "", "soapbox": "73 GL",
    "cab2_exch_sent": "none", "cab2_exch_rcvd": "log",
    "theme": "Light (Zi)",
    "cat_enabled": False, "cat_protocol": "Yaesu CAT",
    "cat_port": "", "cat_baud": 38400, "cat_poll": 2000,
    "cat_civaddr": "94", "cat_hamlib_host": "localhost",
    "cat_hamlib_port": 4532, "first_run": True,
}

DEFAULT_CONTESTS = {
    # ── Log Simplu ────────────────────────────────────────────────────────────
    "simplu": {
        "name_ro": "Log Simplu", "name_en": "Simple Log",
        "contest_type": "Simplu", "cabrillo_name": "Simple Log",
        "categories": ["Individual"], "scoring_mode": "none",
        "points_per_qso": 1, "min_qso": 0,
        "allowed_bands": list(BANDS_ALL), "allowed_modes": list(MODES_ALL),
        "required_stations": [], "special_scoring": {},
        "use_serial": False, "use_county": False, "county_list": [],
        "multiplier_type": "none", "band_points": {},
        "exchange_format": "none", "is_default": True,
        "description": "Log general - fara reguli de concurs",
    },

    # ── Maraton Ion Creangă ───────────────────────────────────────────────────
    # 80m SSB, max 1 QSO/zi/statie, 2-15 Martie, YO8KZG
    "maraton": {
        "name_ro": "Maraton Ion Creanga", "name_en": "Marathon Ion Creanga",
        "contest_type": "Maraton", "cabrillo_name": "MARATON ION CREANGA",
        "categories": ["A. Seniori YO","B. YL","C. Juniori YO","D. Club","E. DX","F. Receptori"],
        "scoring_mode": "maraton", "points_per_qso": 1, "min_qso": 100,
        "allowed_bands": ["80m"], "allowed_modes": ["SSB"],
        "required_stations": [], "special_scoring": {},
        "use_serial": False, "use_county": True,
        "county_list": ["AB","AR","AG","BC","BH","BN","BT","BV","BR","BZ","CS","CL","CJ","CT","CV","DB","DJ","GL","GR","GJ","HR","HD","IL","IS","IF","MM","MH","MS","NT","OT","PH","SM","SJ","SB","SV","TR","TM","TL","VS","VL","VN","B"],
        "multiplier_type": "county", "band_points": {},
        "exchange_format": "county",
        "max_qso_per_day_per_call": 1,
        "period": "2 MAR - 15 MAR", "organizer": "YO8KZG",
        "is_default": False,
        "description": "80m SSB - max 1 QSO/zi/statie - multiplicatori judete",
    },

    # ── Cupa Elevului ─────────────────────────────────────────────────────────
    # 30 Martie, Palatul Copiilor Piatra Neamt
    "cupa_elevului": {
        "name_ro": "Cupa Elevului", "name_en": "Student Cup",
        "contest_type": "Cupa", "cabrillo_name": "CUPA ELEVULUI",
        "categories": ["Elev","Junior","Individual","Echipa"],
        "scoring_mode": "per_qso", "points_per_qso": 1, "min_qso": 0,
        "allowed_bands": list(BANDS_ALL), "allowed_modes": list(MODES_ALL),
        "required_stations": [], "special_scoring": {},
        "use_serial": True, "use_county": True,
        "county_list": ["AB","AR","AG","BC","BH","BN","BT","BV","BR","BZ","CS","CL","CJ","CT","CV","DB","DJ","GL","GR","GJ","HR","HD","IL","IS","IF","MM","MH","MS","NT","OT","PH","SM","SJ","SB","SV","TR","TM","TL","VS","VL","VN","B"],
        "multiplier_type": "county", "band_points": {},
        "exchange_format": "serial",
        "period": "30 MAR", "organizer": "Palatul Copiilor Piatra Neamt",
        "is_default": False,
        "description": "Concurs local Piatra Neamt - schimb numere de serie",
    },

    # ── YO DX HF Contest ─────────────────────────────────────────────────────
    # 22-23 August, FRR, multiband SSB+CW
    "yo_dx_hf": {
        "name_ro": "YO DX HF Contest", "name_en": "YO DX HF Contest",
        "contest_type": "DX", "cabrillo_name": "YO-DX-HF",
        "categories": ["Single Op All Band","Single Op Single Band","Multi Op","SWL"],
        "scoring_mode": "per_band",
        "band_points": {"160m":4,"80m":4,"40m":3,"20m":3,"15m":2,"10m":2},
        "points_per_qso": 1, "min_qso": 0,
        "allowed_bands": ["160m","80m","40m","20m","15m","10m"],
        "allowed_modes": ["SSB","CW"],
        "required_stations": [], "special_scoring": {},
        "use_serial": True, "use_county": True,
        "county_list": ["AB","AR","AG","BC","BH","BN","BT","BV","BR","BZ","CS","CL","CJ","CT","CV","DB","DJ","GL","GR","GJ","HR","HD","IL","IS","IF","MM","MH","MS","NT","OT","PH","SM","SJ","SB","SV","TR","TM","TL","VS","VL","VN","B"],
        "multiplier_type": "dxcc",
        "exchange_format": "serial_county",
        "period": "22-23 AUG", "organizer": "FRR",
        "is_default": False,
        "description": "Campionat National multiband SSB+CW - multiplicatori DXCC",
    },

    # ── YO VHF/UHF Contest ────────────────────────────────────────────────────
    # Puncte = km distanta din locator Maidenhead
    "yo_vhf": {
        "name_ro": "YO VHF/UHF Contest", "name_en": "YO VHF/UHF Contest",
        "contest_type": "VHF", "cabrillo_name": "YO-VHF-UHF",
        "categories": ["144 MHz","432 MHz","1296 MHz","Multi Band"],
        "scoring_mode": "distance",
        "points_per_qso": 1, "min_qso": 0,
        "allowed_bands": ["2m","70cm","23cm","13cm"],
        "allowed_modes": ["SSB","CW","FM","FT8","FT4","DIGI"],
        "required_stations": [], "special_scoring": {},
        "use_serial": True, "use_county": False, "county_list": [],
        "multiplier_type": "grid",
        "exchange_format": "grid",
        "locator_required": True,
        "period": "lunar", "organizer": "www.uus.ro",
        "is_default": False,
        "description": "Puncte = km distanta calculata din locator Maidenhead",
    },

    # ── Field Day ─────────────────────────────────────────────────────────────
    "field_day": {
        "name_ro": "Field Day", "name_en": "Field Day",
        "contest_type": "Field Day", "cabrillo_name": "FIELD-DAY",
        "categories": ["A","B","C","D","E","F"],
        "scoring_mode": "per_qso", "points_per_qso": 1, "min_qso": 0,
        "allowed_bands": list(BANDS_ALL), "allowed_modes": list(MODES_ALL),
        "required_stations": [], "special_scoring": {},
        "use_serial": True, "use_county": False, "county_list": [],
        "multiplier_type": "none", "band_points": {},
        "exchange_format": "serial",
        "period": "Iun-Iul", "organizer": "ARRL / IARU",
        "is_default": False,
        "description": "Operatii din teren - statii autonome",
    },

    # ── La Multi Ani YO! ──────────────────────────────────────────────────────
    # 2 Ianuarie, FRR
    "la_multi_ani": {
        "name_ro": "La Multi Ani YO!", "name_en": "Happy New Year YO!",
        "contest_type": "Cupa", "cabrillo_name": "LA-MULTI-ANI-YO",
        "categories": ["Individual","Club"],
        "scoring_mode": "per_qso", "points_per_qso": 1, "min_qso": 0,
        "allowed_bands": list(BANDS_ALL), "allowed_modes": list(MODES_ALL),
        "required_stations": [], "special_scoring": {},
        "use_serial": True, "use_county": True,
        "county_list": ["AB","AR","AG","BC","BH","BN","BT","BV","BR","BZ","CS","CL","CJ","CT","CV","DB","DJ","GL","GR","GJ","HR","HD","IL","IS","IF","MM","MH","MS","NT","OT","PH","SM","SJ","SB","SV","TR","TM","TL","VS","VL","VN","B"],
        "multiplier_type": "county", "band_points": {},
        "exchange_format": "serial",
        "period": "2 IAN", "organizer": "FRR",
        "is_default": False,
        "description": "Concurs de Anul Nou - schimb serial + judet",
    },

    # ── Cupa Moldovei ─────────────────────────────────────────────────────────
    # CW+SSB, multiplicatori judete + DXCC, punctaj Moldova vs YO
    "cupa_moldovei": {
        "name_ro": "Cupa Moldovei", "name_en": "Moldova Cup",
        "contest_type": "Cupa", "cabrillo_name": "CUPA MOLDOVEI",
        "categories": ["YO Moldova","Restul YO","DX","SWL"],
        "scoring_mode": "per_qso",
        "points_per_qso": 1,
        "special_scoring": {"YO8": 3, "YO7": 2, "YO9": 2},
        "min_qso": 0,
        "allowed_bands": ["80m","40m","20m"],
        "allowed_modes": ["SSB","CW"],
        "required_stations": [], 
        "use_serial": True, "use_county": True,
        "county_list": ["AB","AR","AG","BC","BH","BN","BT","BV","BR","BZ","CS","CL","CJ","CT","CV","DB","DJ","GL","GR","GJ","HR","HD","IL","IS","IF","MM","MH","MS","NT","OT","PH","SM","SJ","SB","SV","TR","TM","TL","VS","VL","VN","B"],
        "multiplier_type": "county",
        "band_points": {},
        "exchange_format": "serial_county",
        "period": "16 FEB", "organizer": "YO8KAN",
        "is_default": False,
        "description": "CW+SSB - punctaj special Moldova YO8 - multiplicatori judete+DXCC",
    },

    # ── Cupa 1 Decembrie ──────────────────────────────────────────────────────
    "cupa_1_dec": {
        "name_ro": "Cupa 1 Decembrie", "name_en": "1st December Cup",
        "contest_type": "Cupa", "cabrillo_name": "CUPA-1-DECEMBRIE",
        "categories": ["Individual","Club"],
        "scoring_mode": "per_qso", "points_per_qso": 1, "min_qso": 0,
        "allowed_bands": list(BANDS_ALL), "allowed_modes": list(MODES_ALL),
        "required_stations": [], "special_scoring": {},
        "use_serial": True, "use_county": True,
        "county_list": ["AB","AR","AG","BC","BH","BN","BT","BV","BR","BZ","CS","CL","CJ","CT","CV","DB","DJ","GL","GR","GJ","HR","HD","IL","IS","IF","MM","MH","MS","NT","OT","PH","SM","SJ","SB","SV","TR","TM","TL","VS","VL","VN","B"],
        "multiplier_type": "county", "band_points": {},
        "exchange_format": "serial",
        "period": "1 DEC", "organizer": "Asociatia Judeteana Radioamatorism Alba",
        "is_default": False,
        "description": "Ziua Nationala a Romaniei - concurs aniversar",
    },

    # ── Cupa Tomis ────────────────────────────────────────────────────────────
    # Constanta, toleranta 5 min, punctaj variabil
    "cupa_tomis": {
        "name_ro": "Cupa Tomis", "name_en": "Tomis Cup",
        "contest_type": "Cupa", "cabrillo_name": "CUPA TOMIS",
        "categories": ["Individual","YL","Junior","Club"],
        "scoring_mode": "per_qso", "points_per_qso": 1, "min_qso": 0,
        "allowed_bands": list(BANDS_ALL), "allowed_modes": list(MODES_ALL),
        "required_stations": [], "special_scoring": {},
        "use_serial": True, "use_county": True,
        "county_list": ["AB","AR","AG","BC","BH","BN","BT","BV","BR","BZ","CS","CL","CJ","CT","CV","DB","DJ","GL","GR","GJ","HR","HD","IL","IS","IF","MM","MH","MS","NT","OT","PH","SM","SJ","SB","SV","TR","TM","TL","VS","VL","VN","B"],
        "multiplier_type": "county", "band_points": {},
        "exchange_format": "serial",
        "time_tolerance_min": 5,
        "period": "23 FEB", "organizer": "Asociatia Radioclubul Radu Bratu",
        "is_default": False,
        "description": "Constanta - toleranta 5 min - punctaj variabil dupa distanta",
    },

    # ── Concursul Lucian Blaga ────────────────────────────────────────────────
    "lucian_blaga": {
        "name_ro": "Concursul Lucian Blaga", "name_en": "Lucian Blaga Contest",
        "contest_type": "Concurs", "cabrillo_name": "LUCIAN BLAGA",
        "categories": ["Individual","Club"],
        "scoring_mode": "per_qso", "points_per_qso": 1, "min_qso": 0,
        "allowed_bands": list(BANDS_ALL), "allowed_modes": list(MODES_ALL),
        "required_stations": [], "special_scoring": {},
        "use_serial": True, "use_county": True,
        "county_list": ["AB","AR","AG","BC","BH","BN","BT","BV","BR","BZ","CS","CL","CJ","CT","CV","DB","DJ","GL","GR","GJ","HR","HD","IL","IS","IF","MM","MH","MS","NT","OT","PH","SM","SJ","SB","SV","TR","TM","TL","VS","VL","VN","B"],
        "multiplier_type": "county", "band_points": {},
        "exchange_format": "serial",
        "period": "9 MAI", "organizer": "YO5KLB - Sebes",
        "is_default": False,
        "description": "Concurs aniversar Lucian Blaga - 9 Mai - Sebes AB",
    },

    # ── Memorial YO ───────────────────────────────────────────────────────────
    # Noiembrie, FRR / YO DX Club
    "memorial_yo": {
        "name_ro": "Memorial YO", "name_en": "YO Memorial",
        "contest_type": "Memorial", "cabrillo_name": "MEMORIAL YO",
        "categories": ["Individual","YL","Junior","Club","DX"],
        "scoring_mode": "per_band",
        "band_points": {"160m":4,"80m":4,"40m":3,"20m":3,"15m":2,"10m":2},
        "points_per_qso": 1, "min_qso": 0,
        "allowed_bands": ["160m","80m","40m","20m","15m","10m"],
        "allowed_modes": ["SSB","CW"],
        "required_stations": [], "special_scoring": {},
        "use_serial": True, "use_county": True,
        "county_list": ["AB","AR","AG","BC","BH","BN","BT","BV","BR","BZ","CS","CL","CJ","CT","CV","DB","DJ","GL","GR","GJ","HR","HD","IL","IS","IF","MM","MH","MS","NT","OT","PH","SM","SJ","SB","SV","TR","TM","TL","VS","VL","VN","B"],
        "multiplier_type": "county",
        "band_points": {"160m":4,"80m":4,"40m":3,"20m":3,"15m":2,"10m":2},
        "exchange_format": "serial_county",
        "period": "2 NOV", "organizer": "FRR / YO DX Club",
        "is_default": False,
        "description": "In memoria radioamatorilor YO disparuti - SSB+CW multiband",
    },

    # ── Stafeta (existent dar actualizat) ──────────────────────────────────────
    "stafeta": {
        "name_ro": "Stafeta", "name_en": "Relay Contest",
        "contest_type": "Stafeta", "cabrillo_name": "STAFETA",
        "categories": ["Judet","Club"],
        "scoring_mode": "per_qso", "points_per_qso": 1, "min_qso": 0,
        "allowed_bands": list(BANDS_ALL), "allowed_modes": list(MODES_ALL),
        "required_stations": [], "special_scoring": {},
        "use_serial": True, "use_county": True,
        "county_list": ["AB","AR","AG","BC","BH","BN","BT","BV","BR","BZ","CS","CL","CJ","CT","CV","DB","DJ","GL","GR","GJ","HR","HD","IL","IS","IF","MM","MH","MS","NT","OT","PH","SM","SJ","SB","SV","TR","TM","TL","VS","VL","VN","B"],
        "multiplier_type": "county", "band_points": {},
        "exchange_format": "county",
        "is_default": False,
        "description": "Concurs in echipe pe judete",
    },
    # ════════════════════════════════════════════════════════════════════════
    # CONCURSURI SUPLIMENTARE — radioamator.ro 2026
    # ════════════════════════════════════════════════════════════════════════

    # ── Cupa Napoca ───────────────────────────────────────────────────────────
    "cupa_napoca": {
        "name_ro": "Cupa Napoca", "name_en": "Napoca Cup",
        "contest_type": "Cupa", "cabrillo_name": "CUPA NAPOCA",
        "categories": ["Individual","YL","Junior","Club"],
        "scoring_mode": "per_qso", "points_per_qso": 1, "min_qso": 0,
        "allowed_bands": list(BANDS_ALL), "allowed_modes": list(MODES_ALL),
        "required_stations": [], "special_scoring": {},
        "use_serial": True, "use_county": True,
        "county_list": ["AB","AR","AG","BC","BH","BN","BT","BV","BR","BZ","CS","CL","CJ","CT","CV","DB","DJ","GL","GR","GJ","HR","HD","IL","IS","IF","MM","MH","MS","NT","OT","PH","SM","SJ","SB","SV","TR","TM","TL","VS","VL","VN","B"],
        "multiplier_type": "county", "band_points": {},
        "exchange_format": "serial",
        "period": "2-3 MAI", "organizer": "CSM Cluj Napoca",
        "is_default": False,
        "description": "Cupa multiband Cluj Napoca - schimb serial+judet",
    },

    # ── YO UHF-SHF Marathon ───────────────────────────────────────────────────
    "yo_uhf_shf": {
        "name_ro": "YO UHF-SHF Marathon", "name_en": "YO UHF-SHF Marathon",
        "contest_type": "VHF", "cabrillo_name": "YO-UHF-SHF-MARATHON",
        "categories": ["432 MHz","1296 MHz","2.3 GHz","3.4 GHz","5.7 GHz","Multi Band"],
        "scoring_mode": "distance",
        "points_per_qso": 1, "min_qso": 0,
        "allowed_bands": ["70cm","23cm","13cm","9cm","6cm"],
        "allowed_modes": ["SSB","CW","FM","FT8","FT4","DIGI"],
        "required_stations": [], "special_scoring": {},
        "use_serial": True, "use_county": False, "county_list": [],
        "multiplier_type": "grid",
        "exchange_format": "grid",
        "locator_required": True,
        "period": "lunar (12 runde)", "organizer": "YO SHF Team",
        "is_default": False,
        "description": "Maraton UHF-SHF 12 runde anuale - puncte = km din locator",
    },

    # ── Cupa Fundatiei Zamolxes ───────────────────────────────────────────────
    "zamolxes": {
        "name_ro": "Cupa Fundatiei Zamolxes", "name_en": "Zamolxes Foundation Cup",
        "contest_type": "VHF", "cabrillo_name": "ZAMOLXES",
        "categories": ["144 MHz Individual","144 MHz Club"],
        "scoring_mode": "distance",
        "points_per_qso": 1, "min_qso": 0,
        "allowed_bands": ["2m"],
        "allowed_modes": ["SSB","CW","FM","FT8","FT4"],
        "required_stations": [], "special_scoring": {},
        "use_serial": True, "use_county": False, "county_list": [],
        "multiplier_type": "grid",
        "exchange_format": "grid",
        "locator_required": True,
        "period": "7-8 MAR", "organizer": "Fundatia Zamolxes",
        "is_default": False,
        "description": "144 MHz - puncte = km distanta din locator Maidenhead",
    },

    # ── Pro Digital Contest ───────────────────────────────────────────────────
    "pro_digital": {
        "name_ro": "Pro Digital Contest", "name_en": "Pro Digital Contest (PDC)",
        "contest_type": "Digital", "cabrillo_name": "PRO-DIGITAL-CONTEST",
        "categories": ["Single Op","Multi Op","SWL"],
        "scoring_mode": "per_qso", "points_per_qso": 2, "min_qso": 0,
        "allowed_bands": list(BANDS_ALL),
        "allowed_modes": ["FT8","FT4","RTTY","PSK31","PSK63","DIGI"],
        "required_stations": [], "special_scoring": {},
        "use_serial": True, "use_county": True,
        "county_list": ["AB","AR","AG","BC","BH","BN","BT","BV","BR","BZ","CS","CL","CJ","CT","CV","DB","DJ","GL","GR","GJ","HR","HD","IL","IS","IF","MM","MH","MS","NT","OT","PH","SM","SJ","SB","SV","TR","TM","TL","VS","VL","VN","B"],
        "multiplier_type": "county", "band_points": {},
        "exchange_format": "serial",
        "period": "17-18 IAN", "organizer": "PRO DIGITAL CLUB",
        "is_default": False,
        "description": "Concurs moduri digitale FT8/FT4/RTTY/PSK",
    },

    # ── Pro CW Contest ────────────────────────────────────────────────────────
    "pro_cw": {
        "name_ro": "Pro CW Contest", "name_en": "Pro CW Contest (PCC)",
        "contest_type": "CW", "cabrillo_name": "PRO-CW-CONTEST",
        "categories": ["Single Op","Multi Op","QRP","SWL"],
        "scoring_mode": "per_qso", "points_per_qso": 2, "min_qso": 0,
        "allowed_bands": ["160m","80m","40m","20m","15m","10m"],
        "allowed_modes": ["CW"],
        "required_stations": [], "special_scoring": {},
        "use_serial": True, "use_county": True,
        "county_list": ["AB","AR","AG","BC","BH","BN","BT","BV","BR","BZ","CS","CL","CJ","CT","CV","DB","DJ","GL","GR","GJ","HR","HD","IL","IS","IF","MM","MH","MS","NT","OT","PH","SM","SJ","SB","SV","TR","TM","TL","VS","VL","VN","B"],
        "multiplier_type": "county", "band_points": {},
        "exchange_format": "serial",
        "period": "5-6 DEC", "organizer": "PRO-CW-CONTEST CLUB",
        "is_default": False,
        "description": "Concurs CW pur - schimb numere seriale + judet",
    },

    # ── Memorial YO2BCT ───────────────────────────────────────────────────────
    "memorial_yo2bct": {
        "name_ro": "Memorial YO2BCT", "name_en": "YO2BCT Memorial",
        "contest_type": "VHF", "cabrillo_name": "MEMORIAL-YO2BCT",
        "categories": ["144 MHz","432 MHz","Multi Band"],
        "scoring_mode": "distance",
        "points_per_qso": 1, "min_qso": 0,
        "allowed_bands": ["2m","70cm"],
        "allowed_modes": ["SSB","CW","FM","FT8"],
        "required_stations": [], "special_scoring": {},
        "use_serial": True, "use_county": False, "county_list": [],
        "multiplier_type": "grid",
        "exchange_format": "grid",
        "locator_required": True,
        "period": "3-4 OCT", "organizer": "YO2KQT Asociatia QSO BANAT",
        "is_default": False,
        "description": "Memorial VHF/UHF - puncte km din locator",
    },

    # ── SSB Diaspora Romaneasca ────────────────────────────────────────────────
    "diaspora": {
        "name_ro": "Concurs SSB Diaspora Romaneasca", "name_en": "Romanian Diaspora SSB",
        "contest_type": "DX", "cabrillo_name": "DIASPORA-SSB",
        "categories": ["YO statii","DX statii","SWL"],
        "scoring_mode": "per_qso",
        "points_per_qso": 1,
        "special_scoring": {"DX": 3, "YO": 1},
        "min_qso": 0,
        "allowed_bands": list(BANDS_ALL),
        "allowed_modes": ["SSB"],
        "required_stations": [], 
        "use_serial": True, "use_county": True,
        "county_list": ["AB","AR","AG","BC","BH","BN","BT","BV","BR","BZ","CS","CL","CJ","CT","CV","DB","DJ","GL","GR","GJ","HR","HD","IL","IS","IF","MM","MH","MS","NT","OT","PH","SM","SJ","SB","SV","TR","TM","TL","VS","VL","VN","B"],
        "multiplier_type": "dxcc", "band_points": {},
        "exchange_format": "serial",
        "period": "31 MAI", "organizer": "YO6TR / M0UDD",
        "is_default": False,
        "description": "SSB Diaspora - conexiunea radioamatorilor YO din lume",
    },

    # ── Campionat National HF Radiotelegrafie ─────────────────────────────────
    "cn_cw": {
        "name_ro": "Campionat National HF Radiotelegrafie", "name_en": "National HF CW Championship",
        "contest_type": "Campionat", "cabrillo_name": "CN-HF-CW",
        "categories": ["Etapa I","Etapa II"],
        "scoring_mode": "per_qso", "points_per_qso": 1, "min_qso": 0,
        "allowed_bands": ["160m","80m","40m","20m","15m","10m"],
        "allowed_modes": ["CW"],
        "required_stations": [], "special_scoring": {},
        "use_serial": True, "use_county": True,
        "county_list": ["AB","AR","AG","BC","BH","BN","BT","BV","BR","BZ","CS","CL","CJ","CT","CV","DB","DJ","GL","GR","GJ","HR","HD","IL","IS","IF","MM","MH","MS","NT","OT","PH","SM","SJ","SB","SV","TR","TM","TL","VS","VL","VN","B"],
        "multiplier_type": "county", "band_points": {},
        "exchange_format": "serial",
        "period": "MAR (2 etape)", "organizer": "FRR",
        "is_default": False,
        "description": "Campionat national CW - doua etape - FRR",
    },

    # ── VHF FT8 Activity Contest ──────────────────────────────────────────────
    "vhf_ft8": {
        "name_ro": "VHF FT8 Activity Contest", "name_en": "VHF FT8 Activity Contest",
        "contest_type": "VHF", "cabrillo_name": "VHF-FT8-ACTIVITY",
        "categories": ["Individual","Club"],
        "scoring_mode": "distance",
        "points_per_qso": 1, "min_qso": 0,
        "allowed_bands": ["2m"],
        "allowed_modes": ["FT8"],
        "required_stations": [], "special_scoring": {},
        "use_serial": True, "use_county": False, "county_list": [],
        "multiplier_type": "grid",
        "exchange_format": "grid",
        "locator_required": True,
        "period": "lunar (12 runde)", "organizer": "Asociatia QSO Banat",
        "is_default": False,
        "description": "VHF FT8 Activity - 12 runde - puncte km locator",
    },

    # ── Concurs CUSTOM (sablon pentru orice concurs nou) ─────────────────────
    "custom": {
        "name_ro": "Concurs Custom", "name_en": "Custom Contest",
        "contest_type": "Custom", "cabrillo_name": "CUSTOM",
        "categories": ["Individual","Club"],
        "scoring_mode": "per_qso", "points_per_qso": 1, "min_qso": 0,
        "allowed_bands": list(BANDS_ALL), "allowed_modes": list(MODES_ALL),
        "required_stations": [], "special_scoring": {},
        "use_serial": True, "use_county": True,
        "county_list": ["AB","AR","AG","BC","BH","BN","BT","BV","BR","BZ","CS","CL","CJ","CT","CV","DB","DJ","GL","GR","GJ","HR","HD","IL","IS","IF","MM","MH","MS","NT","OT","PH","SM","SJ","SB","SV","TR","TM","TL","VS","VL","VN","B"],
        "multiplier_type": "county", "band_points": {},
        "exchange_format": "serial",
        "period": "", "organizer": "",
        "is_default": False,
        "description": "Sablon pentru concurs personalizat - editeaza regulile din Manager Concursuri",
    },
}

try:
    import winsound
    HAS_SOUND = True
except ImportError:
    HAS_SOUND = False


def _normalize_time(raw: str) -> str:
    if not raw:
        return "00:00"
    t = raw.strip().replace(":", "").replace(".", "")
    if not t.isdigit():
        return raw.strip()
    if len(t) <= 2:
        return f"00:{int(t):02d}"
    if len(t) == 3:
        return f"{int(t[0]):02d}:{t[1:]}"
    if len(t) >= 4:
        return f"{t[:2]}:{t[2:4]}"
    return raw.strip()


def _beep(kind="info"):
    if not HAS_SOUND:
        return
    try:
        winsound.MessageBeep({
            "error": 0x10, "warning": 0x30,
            "success": 0x40, "info": 0x0,
        }.get(kind, 0x0))
    except Exception as e:
        logger.debug("beep error: %s", e)


def _center_dialog(dialog, parent=None):
    dialog.update_idletasks()
    dw = dialog.winfo_reqwidth()
    dh = dialog.winfo_reqheight()
    try:
        sw = dialog.winfo_screenwidth()
        sh = dialog.winfo_screenheight()
    except Exception:
        sw, sh = 1366, 768
    if parent:
        try:
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            x = px + (pw - dw) // 2
            y = py + (ph - dh) // 2
        except Exception:
            x = (sw - dw) // 2
            y = (sh - dh) // 2
    else:
        x = (sw - dw) // 2
        y = (sh - dh) // 2
    # Asiguram ca fereastra e vizibila pe ecran
    x = max(10, min(x, sw - dw - 10))
    y = max(10, min(y, sh - dh - 10))
    dialog.geometry(f"+{x}+{y}")


def _responsive_geometry(dialog, parent, iw, ih):
    try:
        sw, sh = dialog.winfo_screenwidth(), dialog.winfo_screenheight()
    except Exception:
        sw, sh = 1366, 768
    w = min(iw, int(sw * 0.92))
    h = min(ih, int(sh * 0.88))
    try:
        dialog.update_idletasks()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
    except Exception:
        x, y = (sw - w) // 2, (sh - h) // 2
    x = max(10, min(x, sw - w - 10))
    y = max(10, min(y, sh - h - 10))
    dialog.geometry(f"{w}x{h}+{x}+{y}")


class App(tk.Tk):
    """Aplicație principală YO Log PRO v19."""

    def __init__(self, dm: DataManager, data_dir: str):
        super().__init__()
        self._dm = dm
        self._data_dir = data_dir

        # ── Stare aplicație ──────────────────────────────────────────────────
        self.cfg = dm.load("config.json", DEFAULT_CFG.copy())
        for k, v in DEFAULT_CFG.items():
            if k not in self.cfg:
                self.cfg[k] = v

        self.contests = dm.load("contests.json", DEFAULT_CONTESTS.copy())
        for k, v in DEFAULT_CONTESTS.items():
            if k not in self.contests:
                self.contests[k] = copy.deepcopy(v)

        if self.cfg.get("contest", "") not in self.contests:
            self.cfg["contest"] = "simplu"

        self.log: list[dict] = dm.load_log(self.cfg.get("contest", "simplu"))
        if not isinstance(self.log, list):
            self.log = []

        self.edit_idx: int | None = None
        self.ent: dict = {}
        self.serial: int = len(self.log) + 1
        self.undo_stack: deque = deque(maxlen=50)

        # ── Widget references ─────────────────────────────────────────────────
        self.info_lbl = self.sc_lbl = self.clk = self.rate_lbl = self.cat_lbl = None
        self.led_c = self.led = self.st_lbl = self.wb_lbl = self.log_btn = None
        self.tree = self.ctx = self.fb_v = self.fm_v = None
        self.cat_v = self.cou_v = self.man_v = self.lang_v = None
        self._sort_col = None
        self._sort_rev = False

        # ── CAT — thread-safe cu queue ────────────────────────────────────────
        self._cat_queue: queue.Queue = queue.Queue()
        self._cat = CATEngine(on_update=self._cat_queue.put)

        # ── Temă ─────────────────────────────────────────────────────────────
        apply_theme(self.cfg.get("theme", "Light (Zi)"),
                    self.cfg.get("custom_colors", {}))
        i18n.set_lang(self.cfg.get("lang", "ro"))

        # ── Font ─────────────────────────────────────────────────────────────
        fs = int(self.cfg.get("fs", 11))
        self.fn = ("Consolas", fs)
        self.fb = ("Consolas", fs, "bold")
        self._ui = UIFactory(self.fn)

        # ── Build UI ─────────────────────────────────────────────────────────
        self._setup_win()
        self._setup_style()
        self._build_menu()
        self._build_ui()
        self._build_ctx()
        self._refresh()

        # ── Bindings ─────────────────────────────────────────────────────────
        self.protocol("WM_DELETE_WINDOW", self._exit)
        self.bind("<Return>",     lambda e: self._add_qso())
        self.bind("<Control-s>",  lambda e: self._fsave())
        self.bind("<Control-z>",  lambda e: self._undo())
        self.bind("<Control-f>",  lambda e: self._search_dlg())
        self.bind("<F2>",          self._cycle_band)
        self.bind("<F3>",          self._cycle_mode)
        self.bind_all("<MouseWheel>", self._on_mousewheel)
        self.bind_all("<Button-4>",  lambda e: self._on_mousewheel(e, +1))
        self.bind_all("<Button-5>",  lambda e: self._on_mousewheel(e, -1))

        # ── Timere ───────────────────────────────────────────────────────────
        self._tick_clock()
        self._tick_save()
        self._process_cat_queue()

        # ── CAT reconnect dacă era activ ─────────────────────────────────────
        if self.cfg.get("cat_enabled") and self.cfg.get("cat_port"):
            try:
                ok, msg = self._cat.connect(self.cfg)
                logger.info("CAT reconnect: %s — %s", ok, msg)
            except Exception as e:
                logger.error("CAT reconnect error: %s", e)

        self.after(100, self._focus_call)

        if self.cfg.get("first_run", True):
            self.after(300, self._first_run_setup)

    # ══════════════════════════════════════════════════════════════════════════
    # CAT — thread-safe
    # ══════════════════════════════════════════════════════════════════════════

    def _process_cat_queue(self):
        """Rulează în firul principal Tkinter — singura metodă care atinge UI din CAT."""
        try:
            while True:
                freq_khz, mode = self._cat_queue.get_nowait()
                self._apply_cat_update(freq_khz, mode)
        except queue.Empty:
            pass
        except Exception as e:
            logger.error("CAT queue processing error: %s", e)
        self.after(200, self._process_cat_queue)

    def _apply_cat_update(self, freq_khz: str, mode: str):
        """Actualizează UI-ul cu date noi de la radio — sigur, rulează în firul UI."""
        try:
            if not self.winfo_exists():
                return
            if freq_khz and self.ent.get("freq"):
                cur = self.ent["freq"].get().strip()
                if cur != freq_khz:
                    self.ent["freq"].delete(0, "end")
                    self.ent["freq"].insert(0, freq_khz)
                    self._on_freq_out()

            if mode and self.ent.get("mode"):
                cc = self._cc()
                allowed = cc.get("allowed_modes", MODES_ALL)
                m = mode if mode in allowed else ("SSB" if "SSB" in allowed else None)
                if m and self.ent["mode"].get() != m:
                    self.ent["mode"].set(m)
                    self._on_mode_change()

            if self.cat_lbl:
                self.cat_lbl.config(
                    text=f" {freq_khz} kHz  {mode}",
                    fg=TH["ok"])
        except Exception as e:
            logger.debug("CAT UI update error: %s", e)

    # ══════════════════════════════════════════════════════════════════════════
    # Setup fereastră
    # ══════════════════════════════════════════════════════════════════════════

    def _setup_win(self):
        self.title(i18n.t("app_title"))
        self.configure(bg=TH["bg"])
        geo = self.cfg.get("win_geo", "")
        try:
            sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        except Exception:
            sw, sh = 1366, 768
        def_w = max(900, min(1280, int(sw * 0.96)))
        def_h = max(600, min(780, int(sh * 0.92)))
        if geo:
            try:
                self.geometry(geo)
            except Exception:
                self.geometry(f"{def_w}x{def_h}")
        else:
            self.geometry(f"{def_w}x{def_h}")
        self.minsize(max(700, int(sw * 0.55)), max(480, int(sh * 0.60)))

    def _setup_style(self):
        setup_ttk_style(self.fn)

    # ══════════════════════════════════════════════════════════════════════════
    # Meniu
    # ══════════════════════════════════════════════════════════════════════════

    def _build_menu(self):
        mb = tk.Menu(self)
        self.config(menu=mb)

        # Concursuri
        cm = tk.Menu(mb, tearoff=0)
        mb.add_cascade(label=i18n.t("contests"), menu=cm)
        cm.add_command(label=i18n.t("contest_mgr"), command=self._mgr)
        cm.add_separator()
        for cid, cd in self.contests.items():
            name = cd.get(f"name_{i18n.get_lang()}", cd.get("name_ro", cid))
            cm.add_command(label=f" {name}",
                           command=lambda c=cid: self._switch_contest(c))

        # Log
        lm = tk.Menu(mb, tearoff=0)
        mb.add_cascade(label="Log", menu=lm)
        lm.add_command(label="Log Nou", command=self._new_log_dlg)
        lm.add_separator()
        lm.add_command(label="Salvează acum",
                       command=lambda: self._dm.save_log(self._cid(), self.log))

        # CAT
        cm2 = tk.Menu(mb, tearoff=0)
        mb.add_cascade(label="CAT", menu=cm2)
        cm2.add_command(label="Setări CAT", command=self._cat_dlg)
        cm2.add_separator()
        cm2.add_command(label="Conectează",
                        command=lambda: self._cat_connect())
        cm2.add_command(label="Deconectează",
                        command=lambda: self._cat_disconnect())

        # Teme
        tm2 = tk.Menu(mb, tearoff=0)
        mb.add_cascade(label=" Teme", menu=tm2)
        tm2.add_command(label=" Editor teme și culori", command=self._theme_dlg)
        tm2.add_separator()
        for tnm in THEMES.keys():
            tm2.add_command(label=tnm,
                            command=lambda t=tnm: self._apply_theme_quick(t))

        # Instrumente
        tm = tk.Menu(mb, tearoff=0)
        mb.add_cascade(label=i18n.t("tools"), menu=tm)
        tm.add_command(label=i18n.t("search"),    command=self._search_dlg)
        tm.add_command(label=i18n.t("timer"),     command=self._timer_dlg)
        tm.add_separator()
        tm.add_command(label=i18n.t("imp_adif"),  command=self._import_adif)
        tm.add_command(label=i18n.t("imp_csv"),   command=self._import_csv)
        tm.add_command(label=i18n.t("imp_cab"),   command=self._import_cabrillo)
        tm.add_separator()
        tm.add_command(label=i18n.t("print_log"), command=self._exp_print)
        tm.add_command(label=i18n.t("verify"),    command=self._verify_hash)
        tm.add_separator()
        tm.add_command(label=i18n.t("clear_log"), command=self._clear_log)

        # Meniu Avansat — funcționalități v19
        v19m = tk.Menu(mb, tearoff=0)
        mb.add_cascade(label=" Avansat", menu=v19m)
        v19m.add_command(label=" Log Editor dedicat",  command=self._open_log_editor)
        v19m.add_command(label=" Callbook Lookup",     command=self._open_callbook)
        v19m.add_separator()
        v19m.add_command(label=" Band Map",            command=self._open_bandmap)
        v19m.add_command(label=" DX Cluster",          command=self._open_cluster)
        v19m.add_separator()
        v19m.add_command(label=" Scor Live",           command=self._open_live_score)
        v19m.add_command(label=" Rate QSO Stats",      command=self._open_rate_stats)
        v19m.add_separator()
        v19m.add_command(label=" Actualizare Callbook ANCOM", command=self._update_callbook_dlg)

        # Ajutor
        hm = tk.Menu(mb, tearoff=0)
        mb.add_cascade(label=i18n.t("help"), menu=hm)
        hm.add_command(label=i18n.t("about"),            command=self._about)
        hm.add_separator()
        hm.add_command(label="🔄 Verifică actualizări…", command=self._check_updates)
        hm.add_separator()
        hm.add_command(label="Exit",                      command=self._exit)

    # ══════════════════════════════════════════════════════════════════════════
    # Build UI principal
    # ══════════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        self._build_hdr()
        self._build_inp()
        self._build_flt()
        self._build_tree()
        self._build_btns()

    def _build_hdr(self):
        h = tk.Frame(self, bg=TH["header_bg"], pady=5)
        h.pack(fill="x")

        lf = tk.Frame(h, bg=TH["header_bg"])
        lf.pack(side="left", padx=10)
        self.led_c = tk.Canvas(lf, width=14, height=14,
                                bg=TH["header_bg"], highlightthickness=0)
        self.led = self.led_c.create_oval(1, 1, 13, 13,
                                           fill=TH["led_on"], outline="")
        self.led_c.pack(side="left", padx=(0, 5))
        self.st_lbl = tk.Label(lf, text=i18n.t("online"),
                                bg=TH["header_bg"], fg=TH["led_on"], font=self.fn)
        self.st_lbl.pack(side="left")
        self.info_lbl = tk.Label(lf, text="",
                                  bg=TH["header_bg"], fg=TH["fg"], font=self.fn)
        self.info_lbl.pack(side="left", padx=12)

        rf = tk.Frame(h, bg=TH["header_bg"])
        rf.pack(side="right", padx=10)
        self.clk = tk.Label(rf, text="UTC 00:00:00",
                             bg=TH["header_bg"], fg=TH["gold"],
                             font=("Consolas", 12, "bold"))
        self.clk.pack(side="right", padx=8)
        self.rate_lbl = tk.Label(rf, text="",
                                  bg=TH["header_bg"], fg=TH["ok"],
                                  font=("Consolas", 10))
        self.rate_lbl.pack(side="right", padx=8)
        self.cat_lbl = tk.Label(rf, text="CAT: OFF",
                                 bg=TH["header_bg"], fg=TH["err"],
                                 font=("Consolas", 10))
        self.cat_lbl.pack(side="right", padx=8)

    def _build_inp(self):
        ip = tk.Frame(self, bg=TH["bg"], pady=8)
        ip.pack(fill="x", padx=10)
        r1 = tk.Frame(ip, bg=TH["bg"])
        r1.pack(fill="x")
        cc = self._cc()

        # Call
        cf = tk.Frame(r1, bg=TH["bg"])
        cf.pack(side="left", padx=3)
        tk.Label(cf, text=i18n.t("call"),
                 bg=TH["bg"], fg=TH["fg"], font=self.fb).pack()
        self.ent["call"] = tk.Entry(
            cf, width=15, bg=TH["entry_bg"], fg=TH["gold"],
            font=("Consolas", int(self.fn[1]) + 2, "bold"),
            insertbackground="white", justify="center", relief="solid", bd=1)
        self.ent["call"].pack(ipady=3)
        self.ent["call"].bind("<KeyRelease>", self._on_call_key)
        self.wb_lbl = tk.Label(cf, text="", bg=TH["bg"], fg=TH["err"],
                                font=("Consolas", 9))
        self.wb_lbl.pack()
        tk.Button(cf, text=" Callbook", command=lambda: self._open_callbook(),
                  bg="#1a237e", fg="white", font=("Consolas", 8)).pack(pady=(1, 0))

        # Freq
        ff = tk.Frame(r1, bg=TH["bg"])
        ff.pack(side="left", padx=3)
        tk.Label(ff, text=i18n.t("freq"),
                 bg=TH["bg"], fg=TH["fg"], font=self.fn).pack()
        self.ent["freq"] = tk.Entry(ff, width=9, bg=TH["entry_bg"],
                                     fg=TH["fg"], font=self.fn,
                                     insertbackground=TH["fg"], justify="center")
        self.ent["freq"].pack()
        self.ent["freq"].bind("<FocusOut>", self._on_freq_out)
        self.ent["freq"].bind("<Return>", lambda e: self._send_freq_to_radio())

        # Band
        ab = cc.get("allowed_bands", BANDS_ALL)
        bf2 = tk.Frame(r1, bg=TH["bg"])
        bf2.pack(side="left", padx=3)
        tk.Label(bf2, text=i18n.t("band"),
                 bg=TH["bg"], fg=TH["fg"], font=self.fn).pack()
        self.ent["band"] = ttk.Combobox(bf2, values=ab,
                                         state="readonly", width=6, font=self.fn)
        self.ent["band"].set(ab[0] if ab else "40m")
        self.ent["band"].pack()
        self.ent["band"].bind("<<ComboboxSelected>>", self._on_band_change)

        # Mode
        am = cc.get("allowed_modes", MODES_ALL)
        mf2 = tk.Frame(r1, bg=TH["bg"])
        mf2.pack(side="left", padx=3)
        tk.Label(mf2, text=i18n.t("mode"),
                 bg=TH["bg"], fg=TH["fg"], font=self.fn).pack()
        self.ent["mode"] = ttk.Combobox(mf2, values=am,
                                         state="readonly", width=6, font=self.fn)
        self.ent["mode"].set(am[0] if am else "SSB")
        self.ent["mode"].pack()
        self.ent["mode"].bind("<<ComboboxSelected>>", self._on_mode_change)

        # RST
        drst = RST_DEFAULTS.get(am[0] if am else "SSB", "59")
        for k, lb in [("rst_s", i18n.t("rst_s")), ("rst_r", i18n.t("rst_r"))]:
            frame = tk.Frame(r1, bg=TH["bg"])
            frame.pack(side="left", padx=3)
            tk.Label(frame, text=lb, bg=TH["bg"], fg=TH["fg"],
                     font=self.fn).pack()
            e = tk.Entry(frame, width=5, bg=TH["entry_bg"],
                         fg=TH["fg"], font=self.fn,
                         insertbackground=TH["fg"], justify="center")
            e.insert(0, drst)
            e.pack()
            self.ent[k] = e

        # Seriale (opțional)
        if cc.get("use_serial"):
            for k, lb in [("ss", i18n.t("serial_s")), ("sr", i18n.t("serial_r"))]:
                frame = tk.Frame(r1, bg=TH["bg"])
                frame.pack(side="left", padx=3)
                tk.Label(frame, text=lb, bg=TH["bg"],
                         fg=TH["fg"], font=self.fn).pack()
                e = tk.Entry(frame, width=5, bg=TH["entry_bg"],
                             fg=TH["fg"], font=self.fn,
                             insertbackground=TH["fg"], justify="center")
                if k == "ss":
                    e.insert(0, str(self.serial))
                e.pack()
                self.ent[k] = e

        # Notă / Locator
        nf = tk.Frame(r1, bg=TH["bg"])
        nf.pack(side="left", padx=3)
        tk.Label(nf, text=i18n.t("note"),
                 bg=TH["bg"], fg=TH["fg"], font=self.fn).pack()
        self.ent["note"] = tk.Entry(nf, width=13, bg=TH["entry_bg"],
                                     fg=TH["fg"], font=self.fn,
                                     insertbackground=TH["fg"], justify="center")
        self.ent["note"].pack()

        # Manual + LOG button
        rbf = tk.Frame(r1, bg=TH["bg"])
        rbf.pack(side="left", padx=6)
        self.man_v = tk.BooleanVar(value=self.cfg.get("manual_dt", False))
        tk.Checkbutton(rbf, text=i18n.t("manual"), variable=self.man_v,
                       bg=TH["bg"], fg=TH["fg"],
                       selectcolor=TH["entry_bg"],
                       activebackground=TH["bg"],
                       command=self._tog_man).pack()
        # width=0 + fill="x" = se intinde sa umple containerul
        self.log_btn = tk.Button(rbf, text=i18n.t("log"),
                                  command=self._add_qso,
                                  bg=TH["accent"], fg="white",
                                  font=self.fb, padx=4)
        self.log_btn.pack(pady=1, fill="x", padx=2)
        tk.Button(rbf, text=i18n.t("reset"),
                  command=self._full_clr,
                  bg=TH["btn_bg"], fg=TH["btn_fg"],
                  font=self.fn, padx=4).pack(pady=1, fill="x", padx=2)

        # Rândul 2: dată, oră, categorie
        r2 = tk.Frame(ip, bg=TH["bg"])
        r2.pack(fill="x", pady=(6, 0))
        tk.Label(r2, text=i18n.t("date_l"),
                 bg=TH["bg"], fg=TH["fg"], font=self.fn).pack(side="left", padx=3)
        self.ent["date"] = tk.Entry(r2, width=11, bg=TH["entry_bg"],
                                     fg=TH["fg"], font=self.fn,
                                     justify="center", state="disabled")
        self.ent["date"].pack(side="left", padx=2)
        self._cal_btn = tk.Button(r2, text="📅", bg=TH["btn_bg"],
                                   fg=TH.get("gold", "#f39c12"),
                                   font=("Segoe UI Emoji", 12),
                                   bd=0, relief="flat", cursor="hand2",
                                   activebackground=TH.get("accent", "#1a5276"),
                                   activeforeground="white",
                                   command=self._open_calendar)
        self._cal_btn.pack(side="left", padx=(0, 4))
        self._cal_btn.bind("<Enter>", lambda e: self._cal_btn.config(bg=TH.get("accent","#1a5276")))
        self._cal_btn.bind("<Leave>", lambda e: self._cal_btn.config(bg=TH["btn_bg"]))

        tk.Label(r2, text=i18n.t("time_l"),
                 bg=TH["bg"], fg=TH["fg"], font=self.fn).pack(side="left", padx=3)
        self.ent["time"] = tk.Entry(r2, width=7, bg=TH["entry_bg"],
                                     fg=TH["fg"], font=self.fn,
                                     justify="center", state="disabled")
        self.ent["time"].pack(side="left", padx=2)
        self.ent["time"].bind("<FocusOut>", lambda e: self._auto_format_time())
        self.ent["time"].bind("<Return>",   lambda e: self._auto_format_time())

        now = datetime.datetime.utcnow()
        for k, v in [("date", now.strftime("%Y-%m-%d")),
                     ("time", now.strftime("%H:%M"))]:
            self.ent[k].config(state="normal")
            self.ent[k].insert(0, v)
            if not self.man_v.get():
                self.ent[k].config(state="disabled")

        if not self.man_v.get():
            self._cal_btn.config(state="disabled")

        # Categorie
        tk.Label(r2, text=i18n.t("category"),
                 bg=TH["bg"], fg=TH["fg"], font=self.fn).pack(side="left", padx=(12, 3))
        cats = cc.get("categories", ["Individual"]) or ["Individual"]
        saved_cat = min(self.cfg.get("cat", 0), max(0, len(cats) - 1))
        self.cat_v = tk.StringVar(value=cats[saved_cat])
        ttk.Combobox(r2, textvariable=self.cat_v,
                     values=cats, state="readonly", width=20).pack(side="left", padx=2)

        # Județ (opțional)
        if cc.get("use_county"):
            tk.Label(r2, text=i18n.t("county"),
                     bg=TH["bg"], fg=TH["fg"], font=self.fn).pack(side="left", padx=(8, 3))
            self.cou_v = tk.StringVar(value=self.cfg.get("county", "NT"))
            ttk.Combobox(r2, textvariable=self.cou_v,
                         values=cc.get("county_list", []),
                         state="readonly", width=6).pack(side="left", padx=2)

        tk.Button(r2, text=i18n.t("save_cat"),
                  command=self._save_cat,
                  bg=TH["btn_bg"], fg="white",
                  font=("Consolas", 10)).pack(side="left", padx=8)

    def _build_flt(self):
        ff = tk.Frame(self, bg=TH["bg"])
        ff.pack(fill="x", padx=10, pady=(1, 0))

        tk.Label(ff, text=i18n.t("f_band"),
                 bg=TH["bg"], fg=TH["fg"],
                 font=("Consolas", 10)).pack(side="left")
        self.fb_v = tk.StringVar(value=i18n.t("all"))
        fb = ttk.Combobox(ff, textvariable=self.fb_v,
                           values=[i18n.t("all")] + self._cc().get("allowed_bands", BANDS_ALL),
                           state="readonly", width=7)
        fb.pack(side="left", padx=3)
        fb.bind("<<ComboboxSelected>>", lambda e: self._refresh())

        tk.Label(ff, text=i18n.t("f_mode"),
                 bg=TH["bg"], fg=TH["fg"],
                 font=("Consolas", 10)).pack(side="left", padx=(8, 0))
        self.fm_v = tk.StringVar(value=i18n.t("all"))
        fm = ttk.Combobox(ff, textvariable=self.fm_v,
                           values=[i18n.t("all")] + self._cc().get("allowed_modes", MODES_ALL),
                           state="readonly", width=7)
        fm.pack(side="left", padx=3)
        fm.bind("<<ComboboxSelected>>", lambda e: self._refresh())

        self.sc_lbl = tk.Label(ff, text="",
                                bg=TH["bg"], fg=TH["gold"],
                                font=("Consolas", 11, "bold"))
        self.sc_lbl.pack(side="right", padx=8)

    def _build_tree(self):
        tf = tk.Frame(self, bg=TH["bg"])
        tf.pack(fill="both", expand=True, padx=10, pady=3)
        cc  = self._cc()
        us  = cc.get("use_serial", False)
        hs  = cc.get("scoring_mode", "none") != "none"

        cols  = ["nr", "call", "freq", "band", "mode", "rst_s", "rst_r"]
        hdrs  = [i18n.t("nr"), i18n.t("call"), i18n.t("freq"),
                 i18n.t("band"), i18n.t("mode"), i18n.t("rst_s"), i18n.t("rst_r")]
        wids  = [38, 115, 75, 55, 55, 45, 45]

        if us:
            cols += ["ss", "sr"]
            hdrs += [i18n.t("serial_s"), i18n.t("serial_r")]
            wids += [45, 45]

        cols += ["note", "country", "date", "time"]
        hdrs += [i18n.t("note"), i18n.t("country"), i18n.t("data"), i18n.t("ora")]
        wids += [95, 95, 80, 50]

        if hs:
            cols.append("pts")
            hdrs.append(i18n.t("pts"))
            wids.append(50)

        self.tree = ttk.Treeview(tf, columns=cols, show="headings",
                                  selectmode="extended")
        for c, h, w in zip(cols, hdrs, wids):
            self.tree.heading(c, text=h,
                              command=lambda col=c: self._sort_tree(col))
            self.tree.column(c, width=w, anchor="center")

        self.tree.tag_configure("dup",  background=TH["dup_bg"])
        self.tree.tag_configure("alt",  background=TH["alt"])
        self.tree.tag_configure("spec", background=TH["spec_bg"])

        sb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", lambda e: self._edit_sel())
        self.tree.bind("<Button-3>", self._on_rclick)
        self.tree.bind("<MouseWheel>",
                       lambda e: self.tree.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        self.tree.bind("<Button-4>", lambda e: self.tree.yview_scroll(-1, "units"))
        self.tree.bind("<Button-5>", lambda e: self.tree.yview_scroll(1, "units"))

    def _sort_tree(self, col: str):
        if self._sort_col == col:
            self._sort_rev = not self._sort_rev
        else:
            self._sort_col = col
            self._sort_rev = False
        items = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        try:
            items.sort(
                key=lambda x: float(x[0]) if x[0].lstrip("-").isdigit() else x[0],
                reverse=self._sort_rev)
        except Exception:
            items.sort(key=lambda x: x[0], reverse=self._sort_rev)
        for idx, (_, k) in enumerate(items):
            self.tree.move(k, "", idx)

    def _build_btns(self):
        try:
            sw = self.winfo_screenwidth()
        except Exception:
            sw = 1366
        compact = sw < 1200
        BFONT = ("Consolas", 8 if compact else 9)
        BPAD  = 1 if compact else 2

        def _btn(parent, text, cmd, color):
            tk.Button(parent, text=text, command=cmd,
                      bg=color, fg="white", font=BFONT,
                      relief="raised", bd=1,
                      activebackground=color).pack(
                side="left", padx=BPAD, pady=1)

        bar_outer  = tk.Frame(self, bg=TH["bg"])
        bar_outer.pack(fill="x", side="bottom")
        bar_canvas = tk.Canvas(bar_outer, bg=TH["bg"],
                                highlightthickness=0,
                                height=76 if compact else 84)
        bar_hsb = ttk.Scrollbar(bar_outer, orient="horizontal",
                                 command=bar_canvas.xview)
        bar_canvas.configure(xscrollcommand=bar_hsb.set)
        bar_hsb.pack(side="bottom", fill="x")
        bar_canvas.pack(side="top", fill="x", expand=True)
        bar_inner = tk.Frame(bar_canvas, bg=TH["bg"])
        bar_win   = bar_canvas.create_window((0, 0), window=bar_inner, anchor="nw")

        def _bar_configure(e):
            bar_canvas.configure(scrollregion=bar_canvas.bbox("all"))
            cr = bar_canvas.bbox("all")
            if cr and cr[2] <= bar_canvas.winfo_width():
                bar_hsb.pack_forget()
            elif not bar_hsb.winfo_ismapped():
                bar_hsb.pack(side="bottom", fill="x")

        bar_inner.bind("<Configure>", _bar_configure)

        bb1 = tk.Frame(bar_inner, bg=TH["bg"])
        bb1.pack(fill="x", padx=4, pady=(4, 1))
        _btn(bb1, i18n.t("settings"),  self._settings,      TH["warn"])
        _btn(bb1, i18n.t("contests"),  self._mgr,            "#C2185B")
        _btn(bb1, "CAT",               self._cat_dlg,        "#1a5276")
        _btn(bb1, "Log Nou",           self._new_log_dlg,    "#2e7d32")
        _btn(bb1, i18n.t("stats"),     self._stats,          "#3F51B5")
        _btn(bb1, i18n.t("validate"),  self._validate,       TH["ok"])
        _btn(bb1, i18n.t("export"),    self._export_dlg,     "#9C27B0")

        bb2 = tk.Frame(bar_inner, bg=TH["bg"])
        bb2.pack(fill="x", padx=4, pady=(1, 2))
        _btn(bb2, i18n.t("import_log"), self._import_menu,   "#E64A19")
        _btn(bb2, i18n.t("undo"),        self._undo,          "#5D4037")
        _btn(bb2, i18n.t("backup"),      self._bak,           "#546E7A")
        _btn(bb2, i18n.t("search"),      self._search_dlg,    "#00796B")
        _btn(bb2, "Timer",               self._timer_dlg,     "#004D40")
        _btn(bb2, "Callbook",            self._open_callbook, "#1a237e")

        bb3 = tk.Frame(bar_inner, bg=TH["bg"])
        bb3.pack(fill="x", padx=4, pady=(1, 4))
        _btn(bb3, "Log Editor",  self._open_log_editor, "#1B5E20")
        _btn(bb3, "Band Map",    self._open_bandmap,    "#006064")
        _btn(bb3, "DX Cluster",  self._open_cluster,    "#01579B")
        _btn(bb3, "Scor Live",   self._open_live_score, "#4A148C")
        _btn(bb3, "Rate Stats",  self._open_rate_stats, "#BF360C")
        _btn(bb3, "Teme",        self._theme_dlg,       "#37474F")

    def _build_ctx(self):
        self.ctx = Menu(self, tearoff=0)
        self.ctx.add_command(label=i18n.t("edit_qso"),   command=self._edit_sel)
        self.ctx.add_command(label=i18n.t("delete_qso"), command=self._del_sel)

    # ══════════════════════════════════════════════════════════════════════════
    # Refresh și update info
    # ══════════════════════════════════════════════════════════════════════════

    def _refresh(self):
        if not self.tree:
            return
        try:
            if not self.tree.winfo_exists():
                return
        except Exception:
            return

        for i in self.tree.get_children():
            self.tree.delete(i)

        cc = self._cc()
        hs = cc.get("scoring_mode", "none") != "none"
        us = cc.get("use_serial", False)
        fb = self.fb_v.get() if self.fb_v else i18n.t("all")
        fm = self.fm_v.get() if self.fm_v else i18n.t("all")
        sp_calls = set((cc.get("special_scoring") or {}).keys())
        seen: set = set()

        for i, q in enumerate(self.log):
            b, m, c = q.get("b", ""), q.get("m", ""), q.get("c", "").upper()
            if fb != i18n.t("all") and b != fb:
                continue
            if fm != i18n.t("all") and m != fm:
                continue
            nr  = len(self.log) - i
            key = (c, b, m)
            if key in seen:
                tag = ("dup",)
            elif c in sp_calls:
                tag = ("spec",)
            elif i % 2 == 0:
                tag = ("alt",)
            else:
                tag = ()
            seen.add(key)
            country, _ = DXCC.lookup(c)

            vals = [nr, c, q.get("f", ""), b, m, q.get("s", "59"), q.get("r", "59")]
            if us:
                vals += [q.get("ss", ""), q.get("sr", "")]
            vals += [q.get("n", ""),
                     country if country != "Unknown" else "",
                     q.get("d", ""), q.get("t", "")]
            if hs:
                vals.append(Score.qso(q, cc, self.cfg))

            self.tree.insert("", "end", iid=str(i), values=vals, tags=tag)

        self._upd_info()

    def _upd_info(self):
        cc   = self._cc()
        call = self.cfg.get("call", "NOCALL")
        nm   = cc.get(f"name_{i18n.get_lang()}", cc.get("name_ro", "?"))
        cat  = self.cat_v.get() if self.cat_v else ""

        if self.info_lbl:
            self.info_lbl.config(
                text=f"{call} | {nm} | {cat} | QSO: {len(self.log)}")

        if self.sc_lbl:
            qp, mc, tot = Score.total(self.log, cc, self.cfg)
            if cc.get("scoring_mode", "none") != "none":
                if cc.get("multiplier_type", "none") != "none":
                    self.sc_lbl.config(text=f"Σ {qp}×{mc}={tot}")
                else:
                    self.sc_lbl.config(text=f"Σ {tot}")
            else:
                self.sc_lbl.config(text="")

        if self.rate_lbl and len(self.log) >= 2:
            try:
                dts = sorted([
                    datetime.datetime.strptime(
                        q.get("d", "") + " " + q.get("t", ""), "%Y-%m-%d %H:%M")
                    for q in self.log[:20]
                    if q.get("d") and q.get("t")
                ])
                if len(dts) >= 2:
                    span = (dts[-1] - dts[0]).total_seconds() / 3600
                    if span > 0:
                        self.rate_lbl.config(
                            text=f"{len(dts)/span:.0f} {i18n.t('rate')}")
            except Exception as e:
                logger.debug("Rate calc error: %s", e)

    # ══════════════════════════════════════════════════════════════════════════
    # Logare QSO
    # ══════════════════════════════════════════════════════════════════════════

    def _add_qso(self):
        try:
            self._do_add_qso()
        except Exception as e:
            import traceback
            logger.exception("_do_add_qso error")
            messagebox.showerror(i18n.t("error"),
                                 f"Eroare la logare:\n{e}\n{traceback.format_exc()[-300:]}")

    def _do_add_qso(self):
        if not self.ent:
            return
        call = self.ent["call"].get().upper().strip()
        if not call:
            return
        band = self.ent["band"].get()
        mode = self.ent["mode"].get()
        if not band or not mode:
            return
        if not isinstance(self.log, list):
            self.log = []

        if self.edit_idx is not None and self.edit_idx >= len(self.log):
            self.edit_idx = None
            if self.log_btn:
                self.log_btn.config(text=i18n.t("log"), bg=TH["accent"])

        dup, di = Score.is_dup(self.log, call, band, mode, self.edit_idx)
        if dup and self.edit_idx is None:
            if self.cfg.get("sounds", True) and HAS_SOUND:
                _beep("warning")
            if not messagebox.askyesno(
                    i18n.t("dup_warn"),
                    i18n.t("dup_msg").format(call, band, mode, len(self.log) - di)):
                return

        ds, ts = self._get_dt()
        cc = self._cc()
        qp = {"c": call, "b": band, "m": mode, "n": self.ent["note"].get().upper().strip()}

        if Score.is_new_mult(self.log, qp, cc):
            self._mult_alert(qp)

        q = {
            "c": call, "b": band, "m": mode,
            "s": self.ent["rst_s"].get().strip() or "59",
            "r": self.ent["rst_r"].get().strip() or "59",
            "n": self.ent["note"].get().strip(),
            "d": ds, "t": ts,
            "f": self.ent["freq"].get().strip(),
        }
        if "ss" in self.ent:
            q["ss"] = self.ent["ss"].get().strip()
        if "sr" in self.ent:
            q["sr"] = self.ent["sr"].get().strip()

        if self.edit_idx is not None:
            self.log[self.edit_idx] = q
            self.edit_idx = None
            if self.log_btn:
                self.log_btn.config(text=i18n.t("log"), bg=TH["accent"])
        else:
            self.log.insert(0, q)
            self.undo_stack.append(("add", 0, q))
            self.serial += 1

        self._clr()
        self._refresh()
        self._dm.save_log(self._cid(), self.log)
        logger.info("QSO loggat: %s %s %s", call, band, mode)

    def _clr(self):
        self.ent["call"].delete(0, "end")
        self.ent["note"].delete(0, "end")
        if "ss" in self.ent:
            self.ent["ss"].delete(0, "end")
            self.ent["ss"].insert(0, str(self.serial))
        if "sr" in self.ent:
            self.ent["sr"].delete(0, "end")
        if self.wb_lbl:
            self.wb_lbl.config(text="")
        self.after(50, self._focus_call)

    def _full_clr(self):
        if not self.ent:
            return
        for k in ("call", "note", "freq"):
            if k in self.ent:
                self.ent[k].delete(0, "end")
        mode = self.ent["mode"].get() if self.ent.get("mode") else "SSB"
        rst  = RST_DEFAULTS.get(mode, "59")
        for k in ("rst_s", "rst_r"):
            if self.ent.get(k):
                self.ent[k].delete(0, "end")
                self.ent[k].insert(0, rst)
        if "ss" in self.ent:
            self.ent["ss"].delete(0, "end")
            self.ent["ss"].insert(0, str(self.serial))
        if "sr" in self.ent:
            self.ent["sr"].delete(0, "end")
        if self.wb_lbl:
            self.wb_lbl.config(text="")
        self.after(50, self._focus_call)

    # ══════════════════════════════════════════════════════════════════════════
    # Edit / Delete / Undo
    # ══════════════════════════════════════════════════════════════════════════

    def _edit_sel(self):
        sel = self.tree.selection()
        if not sel:
            return
        try:
            idx = int(sel[0])
        except (ValueError, TypeError):
            return
        if idx < 0 or idx >= len(self.log):
            return
        self.edit_idx = idx
        q = self.log[idx]
        self.ent["call"].delete(0, "end")
        self.ent["call"].insert(0, q.get("c", ""))
        self.ent["freq"].delete(0, "end")
        self.ent["freq"].insert(0, q.get("f", ""))
        cc = self._cc()
        if q.get("b") in cc.get("allowed_bands", BANDS_ALL):
            self.ent["band"].set(q["b"])
        if q.get("m") in cc.get("allowed_modes", MODES_ALL):
            self.ent["mode"].set(q["m"])
        for k, fk in [("rst_s", "s"), ("rst_r", "r"), ("note", "n")]:
            self.ent[k].delete(0, "end")
            self.ent[k].insert(0, q.get(fk, ""))
        for k in ["ss", "sr"]:
            if k in self.ent:
                self.ent[k].delete(0, "end")
                self.ent[k].insert(0, q.get(k, ""))
        if self.log_btn:
            self.log_btn.config(text=i18n.t("update"), bg=TH["warn"])

    def _del_sel(self):
        sel = self.tree.selection()
        if sel and messagebox.askyesno(i18n.t("confirm_del"),
                                       i18n.t("confirm_del_t")):
            for idx in sorted([int(x) for x in sel], reverse=True):
                if 0 <= idx < len(self.log):
                    self.undo_stack.append(("del", idx, copy.deepcopy(self.log[idx])))
                    self.log.pop(idx)
            self._refresh()
            self._dm.save_log(self._cid(), self.log)

    def _undo(self):
        if not self.undo_stack:
            messagebox.showinfo("", i18n.t("undo_empty"))
            return
        act, idx, q = self.undo_stack.pop()
        if act == "add" and 0 <= idx < len(self.log):
            self.log.pop(idx)
        elif act == "del":
            self.log.insert(idx, q)
        self._refresh()
        self._dm.save_log(self._cid(), self.log)

    # ══════════════════════════════════════════════════════════════════════════
    # Handlers câmpuri
    # ══════════════════════════════════════════════════════════════════════════

    def _on_call_key(self, e=None):
        # Normalizare imediată la uppercase (fără întârziere)
        try:
            entry = self.ent.get("call")
            if not entry:
                return
            c   = entry.get().upper()
            pos = entry.index(tk.INSERT)
            entry.delete(0, tk.END)
            entry.insert(0, c)
            try:
                entry.icursor(min(pos, len(c)))
            except Exception:
                pass
        except Exception as e:
            logger.debug("on_call_key uppercase error: %s", e)
            return

        # Debounce 150ms — evită is_dup + DXCC.lookup la fiecare tastă
        if hasattr(self, "_call_key_after") and self._call_key_after:
            try:
                self.after_cancel(self._call_key_after)
            except Exception:
                pass
        self._call_key_after = self.after(150, self._on_call_key_delayed)

    def _on_call_key_delayed(self):
        """Apelat după 150ms debounce — execută lookup DUP + DXCC."""
        self._call_key_after = None
        try:
            entry = self.ent.get("call")
            if not entry:
                return
            c = entry.get().upper()
            if not self.wb_lbl or len(c) < 3:
                if self.wb_lbl:
                    self.wb_lbl.config(text="", fg=TH["err"])
                return
            band = self.ent["band"].get() if self.ent.get("band") else ""
            mode = self.ent["mode"].get() if self.ent.get("mode") else ""
            dup, _ = Score.is_dup(self.log, c, band, mode, self.edit_idx)
            country, _ = DXCC.lookup(c)
            lbl = country if country != "Unknown" else ""
            worked_other = Score.worked_other(self.log, c, band, mode)
            if dup:
                self.wb_lbl.config(text=f" DUP! {lbl}", fg=TH["err"])
            elif worked_other:
                self.wb_lbl.config(text=f" {lbl} (altă bandă)", fg=TH["warn"])
            else:
                self.wb_lbl.config(text=lbl, fg=TH["ok"])
        except Exception as e:
            logger.debug("on_call_key_delayed error: %s", e)

    def _on_freq_out(self, e=None):
        f = self.ent["freq"].get().strip()
        if f:
            b = freq2band(f)
            if b and b in self._cc().get("allowed_bands", BANDS_ALL):
                self.ent["band"].set(b)

    def _send_freq_to_radio(self):
        try:
            f = self.ent["freq"].get().strip() if self.ent.get("freq") else ""
            if f and self._cat.connected:
                self._cat.set_freq(f)
                self._on_freq_out()
        except Exception as e:
            logger.error("send_freq_to_radio error: %s", e)

    def _on_band_change(self, e=None):
        try:
            if not self.ent.get("freq") or self.ent["freq"].get().strip():
                return
            band = self.ent["band"].get()
            self.ent["freq"].delete(0, "end")
            self.ent["freq"].insert(0, str(BAND_FREQ.get(band, "")))
        except Exception as e:
            logger.debug("on_band_change error: %s", e)

    def _on_mode_change(self, e=None):
        try:
            if not self.ent.get("mode"):
                return
            rst = RST_DEFAULTS.get(self.ent["mode"].get(), "59")
            for k in ("rst_s", "rst_r"):
                if self.ent.get(k):
                    self.ent[k].delete(0, "end")
                    self.ent[k].insert(0, rst)
        except Exception as e:
            logger.debug("on_mode_change error: %s", e)
        if self._cat.connected:
            self._cat.set_mode(self.ent["mode"].get())

    def _on_rclick(self, e):
        item = self.tree.identify_row(e.y)
        if item:
            self.tree.selection_set(item)
            self.ctx.post(e.x_root, e.y_root)

    def _on_mousewheel(self, event, direction=None):
        try:
            delta = direction if direction is not None else (
                int(-1 * (event.delta / 120)) if getattr(event, "delta", 0) else -1)
        except Exception:
            delta = -1
        try:
            w     = event.widget
            wtype = type(w).__name__
            if wtype in ("Entry", "TEntry", "Spinbox"):
                return
            if hasattr(w, "yview_scroll") and wtype not in ("Tk", "Frame", "LabelFrame"):
                w.yview_scroll(delta, "units")
                return
        except Exception:
            pass
        try:
            if self.tree and self.tree.winfo_exists():
                self.tree.yview_scroll(delta, "units")
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════════════════
    # Dată / Oră
    # ══════════════════════════════════════════════════════════════════════════

    def _get_dt(self) -> tuple[str, str]:
        if self.man_v and self.man_v.get():
            raw_time  = self.ent["time"].get().strip()
            norm_time = _normalize_time(raw_time)
            self.ent["time"].config(state="normal")
            self.ent["time"].delete(0, "end")
            self.ent["time"].insert(0, norm_time)
            if not self.man_v.get():
                self.ent["time"].config(state="disabled")
            return self.ent["date"].get().strip(), norm_time
        now = datetime.datetime.utcnow()
        return now.strftime("%Y-%m-%d"), now.strftime("%H:%M")

    def _tog_man(self):
        m = self.man_v.get()
        for k in ("date", "time"):
            self.ent[k].config(state="normal" if m else "disabled")
        if hasattr(self, "_cal_btn"):
            self._cal_btn.config(state="normal" if m else "disabled")
        if self.led_c:
            self.led_c.itemconfig(self.led, fill=TH["led_off"] if m else TH["led_on"])
        if self.st_lbl:
            self.st_lbl.config(
                text=i18n.t("offline") if m else i18n.t("online"),
                fg=TH["led_off"] if m else TH["led_on"])
        self.cfg["manual_dt"] = m
        self._dm.save("config.json", self.cfg)

    def _auto_format_time(self):
        if not (self.man_v and self.man_v.get()):
            return
        raw  = self.ent["time"].get().strip()
        norm = _normalize_time(raw)
        if norm != raw:
            self.ent["time"].config(state="normal")
            self.ent["time"].delete(0, "end")
            self.ent["time"].insert(0, norm)

    def _open_calendar(self):
        current = self.ent["date"].get().strip()

        def _set_date(date_str):
            self.ent["date"].config(state="normal")
            self.ent["date"].delete(0, "end")
            self.ent["date"].insert(0, date_str)
            if not self.man_v.get():
                self.ent["date"].config(state="disabled")

        CalendarPopup(self._cal_btn, current, _set_date)

    # ══════════════════════════════════════════════════════════════════════════
    # Ciclare bandă/mod, cycle helpers
    # ══════════════════════════════════════════════════════════════════════════

    def _cycle_band(self, e=None):
        ab  = self._cc().get("allowed_bands", BANDS_ALL) or BANDS_ALL
        cur = self.ent["band"].get()
        self.ent["band"].set(
            ab[(ab.index(cur) + 1) % len(ab)] if cur in ab else ab[0])
        self._on_band_change()

    def _cycle_mode(self, e=None):
        am  = self._cc().get("allowed_modes", MODES_ALL) or MODES_ALL
        cur = self.ent["mode"].get()
        self.ent["mode"].set(
            am[(am.index(cur) + 1) % len(am)] if cur in am else am[0])
        self._on_mode_change()

    # ══════════════════════════════════════════════════════════════════════════
    # CAT UI
    # ══════════════════════════════════════════════════════════════════════════

    def _cat_connect(self):
        if not self.cfg.get("cat_port") and not self.cfg.get("cat_protocol", "").startswith("Hamlib"):
            messagebox.showinfo("CAT", "Configurează portul COM: CAT → Setări CAT")
            self._cat_dlg()
            return
        ok, msg = self._cat.connect(self.cfg)
        if self.cat_lbl:
            self.cat_lbl.config(
                text=f"CAT: {'ON' if ok else 'ERR'}",
                fg=TH["ok"] if ok else TH["err"])
        messagebox.showinfo("CAT", msg)
        logger.info("CAT connect: %s — %s", ok, msg)

    def _cat_disconnect(self):
        self._cat.disconnect()
        if self.cat_lbl:
            self.cat_lbl.config(text="CAT: OFF", fg=TH["err"])

    def _cat_dlg(self):
        d = CATDialog(self, self.cfg, self._cat)
        self.wait_window(d)
        if d.result:
            self.cfg.update(d.result)
            self._dm.save("config.json", self.cfg)
            self._cat.on_update = self._cat_queue.put

    # ══════════════════════════════════════════════════════════════════════════
    # Concursuri
    # ══════════════════════════════════════════════════════════════════════════

    def _cc(self) -> dict:
        return self.contests.get(
            self.cfg.get("contest", "simplu"),
            self.contests.get("simplu", {}))

    def _cid(self) -> str:
        return self.cfg.get("log_id", self.cfg.get("contest", "simplu"))

    def _mgr(self):
        d = ContestMgr(self, self.contests)
        self.wait_window(d)
        if d.result:
            self.contests = d.result
            self._dm.save("contests.json", self.contests)
            self._rebuild()

    def _switch_contest(self, cid: str):
        if messagebox.askyesno("Schimbare concurs", i18n.t("switch_conf")):
            self._dm.save_log(self._cid(), self.log)
            self.cfg["contest"] = cid
            self._dm.save("config.json", self.cfg)
            self.log = self._dm.load_log(cid)
            if not isinstance(self.log, list):
                self.log = []
            self.serial = len(self.log) + 1
            self._rebuild()

    def _new_log_dlg(self):
        self._dm.save_log(self._cid(), self.log)
        d = NewLogDialog(self, self.contests)
        self.wait_window(d)
        if not d.result:
            return
        self.cfg["contest"] = d.result["contest"]
        self.cfg["log_id"]  = d.result["log_id"]
        self._dm.save("config.json", self.cfg)
        self.log = self._dm.load_log(d.result["log_id"])
        if not isinstance(self.log, list):
            self.log = []
        self.serial = 1
        self.undo_stack.clear()
        self._rebuild()

    def _save_cat(self):
        if self.cat_v:
            cats = self._cc().get("categories", [])
            self.cfg["cat"] = (cats.index(self.cat_v.get())
                               if self.cat_v.get() in cats else 0)
        if self.cou_v:
            self.cfg["county"] = self.cou_v.get()
        self._dm.save("config.json", self.cfg)
        self._upd_info()

    # ══════════════════════════════════════════════════════════════════════════
    # Temă / Rebuild
    # ══════════════════════════════════════════════════════════════════════════

    def _apply_theme_quick(self, theme_name: str):
        self.cfg["theme"] = theme_name
        self.cfg["custom_colors"] = {}
        self._dm.save("config.json", self.cfg)
        apply_theme(theme_name)
        self._rebuild()

    def _rebuild(self):
        self.cfg["win_geo"] = self.geometry()
        for w in self.winfo_children():
            w.destroy()
        self.ent = {}
        self.info_lbl = self.sc_lbl = self.clk = self.rate_lbl = self.cat_lbl = None
        self.led_c = self.led = self.st_lbl = self.wb_lbl = self.log_btn = None
        self.tree = self.ctx = self.fb_v = self.fm_v = None
        self.cat_v = self.cou_v = self.man_v = self.lang_v = None
        fs = int(self.cfg.get("fs", 11))
        self.fn = ("Consolas", fs)
        self.fb = ("Consolas", fs, "bold")
        self._ui = UIFactory(self.fn)
        self._setup_style()
        self._build_menu()
        self._build_ui()
        self._build_ctx()
        self._refresh()
        self.after(100, self._focus_call)
        self.bind_all("<MouseWheel>", self._on_mousewheel)
        self.bind_all("<Button-4>",   lambda e: self._on_mousewheel(e, +1))
        self.bind_all("<Button-5>",   lambda e: self._on_mousewheel(e, -1))

    # ══════════════════════════════════════════════════════════════════════════
    # Timere
    # ══════════════════════════════════════════════════════════════════════════

    def _tick_clock(self):
        try:
            if not self.winfo_exists():
                return
            now = datetime.datetime.utcnow()
            if self.clk:
                self.clk.config(text=f"UTC {now.strftime('%H:%M:%S')}")
            # Actualizam data/ora in entry-uri doar in modul Online (man_v=False)
            if self.man_v and not self.man_v.get():
                new_date = now.strftime("%Y-%m-%d")
                new_time = now.strftime("%H:%M")
                for key, val in [("date", new_date), ("time", new_time)]:
                    if key in self.ent:
                        try:
                            self.ent[key].config(state="normal")
                            self.ent[key].delete(0, "end")
                            self.ent[key].insert(0, val)
                            self.ent[key].config(state="disabled")
                        except Exception:
                            pass
            self.after(1000, self._tick_clock)
        except Exception as e:
            logger.debug("tick_clock error: %s", e)

    def _tick_save(self):
        try:
            if not self.winfo_exists():
                return
            self._dm.save_log(self._cid(), self.log)
            self.after(60_000, self._tick_save)
        except Exception as e:
            logger.error("tick_save error: %s", e)

    def _fsave(self):
        self._dm.save_log(self._cid(), self.log)
        self._dm.save("config.json", self.cfg)
        self._dm.save("contests.json", self.contests)
        if self.cfg.get("sounds", True) and HAS_SOUND:
            _beep("success")

    def _focus_call(self):
        try:
            if self.ent.get("call"):
                self.ent["call"].focus_set()
                self.ent["call"].icursor("end")
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════════════════
    # Import / Export
    # ══════════════════════════════════════════════════════════════════════════

    def _export_dlg(self):
        # Stocam categoria curenta in cfg pentru Cabrillo 2.0
        if self.cat_v:
            self.cfg["_current_category"] = self.cat_v.get()
        d = ExportDialog(self, self.log, self.cfg, self._cc(),
                         cab3_dialog_cls=Cab3ConfigDialog,
                         cab2_dialog_cls=Cab2ConfigDialog,
                         dm=self._dm)
        self.wait_window(d)

    def _exp_print(self):
        content = PrintExporter.export(self.log, self.cfg, self._cc())
        fp = filedialog.asksaveasfilename(
            defaultextension=".txt", filetypes=[("Text", "*.txt")],
            initialfile=f"print_{self._cid()}_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.txt")
        if fp:
            try:
                with open(fp, "w", encoding="utf-8") as f:
                    f.write(content)
                messagebox.showinfo(i18n.t("exp_ok"), f"→ {fp}")
            except OSError as e:
                logger.error("Print export error: %s", e)
                messagebox.showerror(i18n.t("error"), str(e))

    def _import_menu(self):
        d = tk.Toplevel(self)
        d.title(i18n.t("import_log"))
        _responsive_geometry(d, self, 300, 220)
        d.configure(bg=TH["bg"])
        d.transient(self)
        for txt, cmd in [
            ("ADIF (.adi/.adif)",  lambda: [d.destroy(), self._import_adif()]),
            ("CSV (.csv)",          lambda: [d.destroy(), self._import_csv()]),
            ("Cabrillo (.log)",    lambda: [d.destroy(), self._import_cabrillo()]),
        ]:
            tk.Button(d, text=txt, command=cmd,
                      bg=TH["accent"], fg="white").pack(pady=6)
        _center_dialog(d, self)

    def _import_adif(self):
        fp = filedialog.askopenfilename(
            filetypes=[("ADIF", "*.adi *.adif"), ("All", "*.*")])
        if fp:
            try:
                with open(fp, "r", encoding="utf-8", errors="replace") as f:
                    self._do_import(Importer.parse_adif(f.read()))
            except OSError as e:
                logger.error("ADIF import error: %s", e)
                messagebox.showerror(i18n.t("error"), str(e))

    def _import_csv(self):
        fp = filedialog.askopenfilename(
            filetypes=[("CSV", "*.csv"), ("All", "*.*")])
        if fp:
            try:
                with open(fp, "r", encoding="utf-8", errors="replace") as f:
                    self._do_import(Importer.parse_csv(f.read()))
            except OSError as e:
                logger.error("CSV import error: %s", e)
                messagebox.showerror(i18n.t("error"), str(e))

    def _import_cabrillo(self):
        fp = filedialog.askopenfilename(
            filetypes=[("Cabrillo", "*.log *.cab"), ("All", "*.*")])
        if fp:
            try:
                with open(fp, "r", encoding="utf-8", errors="replace") as f:
                    self._do_import(Importer.parse_cabrillo(f.read()))
            except OSError as e:
                logger.error("Cabrillo import error: %s", e)
                messagebox.showerror(i18n.t("error"), str(e))

    def _do_import(self, qsos: list[dict]):
        if not qsos:
            messagebox.showwarning("", i18n.t("imp_err"))
            return
        self.log.extend(qsos)
        self.serial = len(self.log) + 1
        self._refresh()
        self._dm.save_log(self._cid(), self.log)
        messagebox.showinfo("", i18n.t("imp_ok").format(len(qsos)))
        logger.info("Importate %d QSO-uri", len(qsos))

    # ══════════════════════════════════════════════════════════════════════════
    # Diverse
    # ══════════════════════════════════════════════════════════════════════════

    def _stats(self):
        StatsDialog(self, self.log, self._cc(), self.cfg)

    def _validate(self):
        if not isinstance(self.log, list):
            self.log = []
        ok, msg, _ = Score.validate(self.log, self._cc(), self.cfg)
        (messagebox.showinfo if ok else messagebox.showwarning)(
            i18n.t("val_result"), msg)

    def _search_dlg(self):
        SearchDialog(self, self.log)

    def _timer_dlg(self):
        TimerDialog(self, self.cfg)

    def _verify_hash(self):
        try:
            h = hashlib.md5(
                json.dumps(self.log, ensure_ascii=False, sort_keys=True)
                .encode("utf-8")).hexdigest()
            messagebox.showinfo(i18n.t("hash_ok"),
                                i18n.t("verify_ok").format(len(self.log), h))
        except Exception as e:
            logger.error("verify_hash error: %s", e)
            messagebox.showerror(i18n.t("error"), str(e))

    def _clear_log(self):
        if self.log and messagebox.askyesno(i18n.t("clear_log"),
                                            i18n.t("clear_conf")):
            self._dm.backup(self._cid(), self.log)
            self.log.clear()
            self.serial = 1
            self.undo_stack.clear()
            self._refresh()
            self._dm.save_log(self._cid(), self.log)

    def _bak(self):
        if self._dm.backup(self._cid(), self.log):
            messagebox.showinfo("OK", i18n.t("bak_ok"))
        else:
            messagebox.showerror(i18n.t("error"), i18n.t("bak_err"))

    def _mult_alert(self, qso: dict):
        if self.cfg.get("sounds", True) and HAS_SOUND:
            _beep("success")
        call = qso.get("c", "")
        messagebox.showinfo(i18n.t("new_mult"),
                            f"* {i18n.t('new_mult')}\n{call}")

    def _open_callbook(self, call=""):
        try:
            from .dialogs.callbook_dlg import CallbookWindow
            if not call and self.ent.get("call"):
                call = self.ent["call"].get().upper().strip()
            CallbookWindow(self, initial_call=call)
        except Exception as e:
            logger.error("Callbook window error: %s", e)
            messagebox.showerror("Callbook", str(e))

    def _settings(self):
        d = SettingsDialog(self, self.cfg)
        self.wait_window(d)
        if d.result:
            self.cfg.update(d.result)
            self._dm.save("config.json", self.cfg)
            i18n.set_lang(self.cfg.get("lang", "ro"))
            self._rebuild()

    def _theme_dlg(self):
        d = ThemeDialog(self,
                        self.cfg.get("theme", "Light (Zi)"),
                        self.cfg.get("custom_colors", {}))
        self.wait_window(d)
        if not d.result:
            return
        self.cfg["theme"]         = d.result["theme"]
        self.cfg["custom_colors"] = d.result["colors"]
        self._dm.save("config.json", self.cfg)
        from .theme import apply_theme
        apply_theme(d.result["theme"], d.result["colors"])
        self._rebuild()

    def _open_log_editor(self):
        LogEditorWindow(
            self,
            log_ref       = self.log,
            contests_ref  = self.contests,
            cfg_ref       = self.cfg,
            on_change     = lambda: self._refresh(),
            cid_getter    = self._cid,
        )

    def _open_bandmap(self):
        BandMapWindow(self,
                      log_getter = lambda: self.log,
                      cfg_getter = lambda: self.cfg)

    def _open_cluster(self):
        def _on_spot(call, freq):
            try:
                if self.ent.get("call"):
                    self.ent["call"].delete(0, "end")
                    self.ent["call"].insert(0, call.upper())
                if self.ent.get("freq") and freq:
                    self.ent["freq"].delete(0, "end")
                    self.ent["freq"].insert(0, str(freq))
                    self._on_freq_out()
                self._focus_call()
            except Exception as e:
                logger.debug("on_spot error: %s", e)
        DXClusterWindow(self, on_spot=_on_spot)

    def _open_live_score(self):
        LiveScorePanel(self,
                       log_getter     = lambda: self.log,
                       cfg_getter     = lambda: self.cfg,
                       contest_getter = self._cc)

    def _open_rate_stats(self):
        RateStatsWindow(self,
                        log_getter = lambda: self.log,
                        cfg_getter = lambda: self.cfg)

    def _update_callbook_dlg(self):
        """Dialog GUI pentru actualizare Callbook ANCOM din fisiere XLSX."""
        from .dialogs.update_callbook_dlg import UpdateCallbookDialog
        d = UpdateCallbookDialog(self)
        self.wait_window(d)

    def _about(self):
        d = tk.Toplevel(self)
        d.title(i18n.t("about"))
        _responsive_geometry(d, self, 540, 380)
        d.configure(bg=TH["bg"])
        d.transient(self)
        d.resizable(False, False)
        _center_dialog(d, self)

        tk.Label(d, text="YO Log PRO v19 -- Full Edition",
                 bg=TH["bg"], fg=TH["accent"],
                 font=("Consolas", 15, "bold")).pack(pady=(16, 4))
        tk.Label(d, text="Professional Multi-Contest Amateur Radio Logger",
                 bg=TH["bg"], fg=TH["fg"],
                 font=("Consolas", 10)).pack()
        tk.Frame(d, bg=TH["accent"], height=2).pack(fill="x", padx=30, pady=8)

        import sys as _sys
        info = [
            ("Dezvoltat de:", "Ardei Constantin-Catalin (YO8ACR)"),
            ("Email:",        "yo8acr@gmail.com"),
            ("",              ""),
            ("Versiune:",     "v19 (2026)"),
            ("Python:",       _sys.version.split()[0] + " / Tkinter GUI"),
            ("Platforme:",    "Windows 7/8/10/11, Linux, macOS"),
        ]
        for lbl, val in info:
            if not lbl and not val:
                tk.Frame(d, bg=TH["bg"], height=4).pack()
                continue
            rf = tk.Frame(d, bg=TH["bg"])
            rf.pack(anchor="w", padx=40, pady=1)
            tk.Label(rf, text=lbl, bg=TH["bg"], fg=TH["fg"],
                     font=("Consolas", 9), width=14, anchor="e").pack(side="left")
            tk.Label(rf, text=val, bg=TH["bg"], fg=TH["gold"],
                     font=("Consolas", 9), anchor="w").pack(side="left", padx=6)

        tk.Frame(d, bg=TH["accent"], height=2).pack(fill="x", padx=30, pady=8)
        tk.Label(d, text="Ctrl+F=Caută  Ctrl+Z=Undo  Ctrl+S=Save  F2=Bandă+  F3=Mod+  Enter=Log",
                 bg=TH["bg"], fg=TH["fg"], font=("Consolas", 8)).pack(pady=(0, 6))
        tk.Button(d, text=i18n.t("close"), command=d.destroy,
                  bg=TH["ok"], fg="white",
                  font=("Consolas", 11)).pack(pady=8)

    def _check_updates(self):
        """Verifică dacă există o versiune nouă pe GitHub și oferă link de download."""
        import threading
        import urllib.request
        import json as _json

        REPO = "acc1311/YOLogPRO"
        API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
        RELEASES_URL = f"https://github.com/{REPO}/releases/latest"

        # Versiunea curentă (din __init__.py sau hardcodat)
        try:
            from yolog import __version__ as _current
        except ImportError:
            _current = "19.0"

        def _fetch():
            try:
                import ssl as _ssl
                # Pe Windows cu Python 3.12+ certificatele CA nu sunt
                # instalate automat - folosim certifi daca e disponibil,
                # altfel dezactivam verificarea doar pt request-ul de update.
                _ctx = _ssl.create_default_context()
                try:
                    import certifi as _certifi
                    _ctx.load_verify_locations(_certifi.where())
                except ImportError:
                    _ctx.check_hostname = False
                    _ctx.verify_mode = _ssl.CERT_NONE

                req = urllib.request.Request(
                    API_URL,
                    headers={"User-Agent": "YOLogPRO-UpdateCheck/1.0",
                             "Accept": "application/vnd.github+json"}
                )
                with urllib.request.urlopen(req, timeout=8, context=_ctx) as resp:
                    data = _json.loads(resp.read().decode())
                tag = data.get("tag_name", "").lstrip("v")
                body = data.get("body", "")[:400]
                assets = [a["name"] for a in data.get("assets", [])]
                self.after(0, lambda: _show(tag, body, assets))
            except Exception as e:
                _emsg = str(e)
                self.after(0, lambda m=_emsg: _show_err(m))

        def _show(latest_tag, notes, assets):
            d = tk.Toplevel(self)
            d.title("Verificare actualizări — YO Log PRO")
            d.configure(bg=TH["bg"])
            d.transient(self)
            d.grab_set()
            try:
                sw, sh = d.winfo_screenwidth(), d.winfo_screenheight()
                w, h = 500, 360
                d.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
            except Exception:
                pass

            fn = ("Consolas", 10)
            tk.Label(d, text="Verificare actualizări", bg=TH["bg"],
                     fg=TH.get("accent","#1abc9c"), font=("Consolas", 13, "bold")).pack(pady=(14, 4))

            # Comparare versiuni
            def _ver_tuple(v):
                try:
                    return tuple(int(x) for x in str(v).split("."))
                except Exception:
                    return (0,)

            cur_t = _ver_tuple(_current)
            lat_t = _ver_tuple(latest_tag)

            if lat_t > cur_t:
                status_text = f"✅ Versiune nouă disponibilă: v{latest_tag}"
                status_fg = TH.get("ok", "#27ae60")
            elif lat_t == cur_t:
                status_text = f"✔ Ești la zi! Versiunea curentă: v{_current}"
                status_fg = TH.get("gold", "#f39c12")
            else:
                status_text = f"ℹ️  Local: v{_current}  |  GitHub: v{latest_tag}"
                status_fg = TH["fg"]

            tk.Label(d, text=status_text, bg=TH["bg"], fg=status_fg,
                     font=("Consolas", 11, "bold")).pack(pady=6)

            if notes:
                tk.Label(d, text="Noutăți:", bg=TH["bg"], fg=TH["fg"],
                         font=("Consolas", 9, "bold")).pack(anchor="w", padx=20)
                txt = tk.Text(d, height=7, bg=TH["entry_bg"], fg=TH["fg"],
                              font=("Consolas", 9), wrap="word",
                              relief="flat", padx=6, pady=4)
                txt.pack(fill="x", padx=20, pady=(2, 8))
                txt.insert("1.0", notes)
                txt.config(state="disabled")

            bf = tk.Frame(d, bg=TH["bg"])
            bf.pack(pady=6)
            if lat_t > cur_t:
                def _open_dl():
                    import webbrowser
                    webbrowser.open(RELEASES_URL)
                tk.Button(bf, text="⬇ Descarcă actualizarea",
                          command=_open_dl,
                          bg=TH.get("ok","#27ae60"), fg="white",
                          font=("Consolas", 10, "bold"),
                          cursor="hand2").pack(side="left", padx=6)
            tk.Button(bf, text="Închide", command=d.destroy,
                      bg=TH["btn_bg"], fg="white", font=fn).pack(side="left", padx=4)

        def _show_err(err_msg):
            messagebox.showwarning(
                "Verificare actualizări",
                f"Nu am putut verifica actualizările:\n\n{err_msg}\n\n"
                f"Verifică manual:\nhttps://github.com/acc1311/YOLogPRO/releases"
            )

        # Status label de așteptare
        try:
            self._status_bar_lbl.config(text="⏳ Verificare actualizări…")
        except Exception:
            pass

        threading.Thread(target=_fetch, daemon=True, name="update-check").start()

    def _first_run_setup(self):
        d = FirstRunDialog(self, self.cfg)
        self.wait_window(d)
        if d.result:
            self.cfg.update(d.result)
            self.cfg["first_run"] = False

            # Intrebare tema la prima deschidere
            from tkinter import simpledialog
            tema_raspuns = messagebox.askyesno(
                "Tema interfata",
                "Doriti tema LUMINOASA (Zi) pentru interfata?\n\n"
                "  DA  -> tema alba (recomandat pentru zi)\n"
                "  NU  -> tema inchisa Dark Blue (recomandat pentru noapte)"
            )
            if tema_raspuns:
                self.cfg["theme"] = "Light (Zi)"
            else:
                self.cfg["theme"] = "Dark Blue (implicit)"
            from yolog.ui.theme import apply_theme, TH as _TH
            apply_theme(self.cfg["theme"], self.cfg.get("custom_colors"))

            self._dm.save("config.json", self.cfg)
            i18n.set_lang(self.cfg.get("lang", "ro"))
            self._rebuild()
            messagebox.showinfo(
                "YO Log PRO v19",
                f"Bun venit, {self.cfg.get('call', '')}!\n\n"
                "YO Log PRO v19 este gata de utilizare.\n73 de YO8ACR!")

    def _exit(self):
        if messagebox.askyesno(i18n.t("exit_t"), i18n.t("exit_m")):
            self.cfg["win_geo"] = self.geometry()
            try:
                self._cat.disconnect()
                self._cat.stop_rigctld()   # opreste rigctld pornit de noi
            except Exception as e:
                logger.debug("CAT disconnect on exit: %s", e)
            self._dm.save_log(self._cid(), self.log)
            self._dm.save("config.json", self.cfg)
            self._dm.save("contests.json", self.contests)
            self._dm.backup(self._cid(), self.log)
            logger.info("YO Log PRO închis normal")
            self.destroy()