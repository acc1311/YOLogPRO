# -*- coding: utf-8 -*-
"""
i18n/__init__.py — Sistem de traduceri
Traduerile sunt in fisiere JSON separate.
Compatible cu PyInstaller: foloseste resource_path pentru a gasi fisierele.
"""
import json
import os
import sys
import logging

logger = logging.getLogger(__name__)

_CACHE: dict = {}
_CURRENT_LANG = "ro"


def _i18n_dir() -> str:
    """Returneaza directorul cu fisierele JSON de traduceri.
    Functioneaza atat din surse Python cat si din EXE PyInstaller.
    """
    # In EXE: fisierele sunt in _MEIPASS/yolog/i18n/
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "yolog", "i18n")  # type: ignore[attr-defined]
    # Din surse: acelasi director cu acest fisier
    return os.path.dirname(__file__)


def _load(lang: str) -> dict:
    if lang not in _CACHE:
        path = os.path.join(_i18n_dir(), f"{lang}.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                _CACHE[lang] = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.error("Nu pot incarca traducerile '%s' din %s: %s", lang, path, e)
            _CACHE[lang] = {}
    return _CACHE[lang]


def set_lang(lang: str) -> None:
    """Seteaza limba activa ('ro' sau 'en')."""
    global _CURRENT_LANG
    _CURRENT_LANG = lang
    _load(lang)


def get_lang() -> str:
    return _CURRENT_LANG


def t(key: str) -> str:
    """Returneaza traducerea pentru cheia data in limba curenta."""
    translations = _load(_CURRENT_LANG)
    result = translations.get(key)
    if result is None and _CURRENT_LANG != "ro":
        result = _load("ro").get(key)
    return result if result is not None else key
