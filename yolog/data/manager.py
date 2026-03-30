# -*- coding: utf-8 -*-
"""
data/manager.py — Gestionare persistenta date
Interfata unificata JSON (prezent) pregatita pentru migrare SQLite.
Toate operatiile de I/O trec prin DataManager — UI-ul nu atinge direct fisiere.
"""
from __future__ import annotations
import os
import re
import json
import copy
import datetime
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def get_data_dir() -> str:
    """
    Returneaza directorul de date al aplicatiei.
    Delega la main.get_data_dir() pentru logica unitara.
    """
    try:
        import main as _main
        return _main.get_data_dir()
    except ImportError:
        import sys
        if getattr(sys, "frozen", False):
            return os.path.dirname(sys.executable)
        return os.path.abspath(".")


class DataManager:
    """
    Gestioneaza toate operatiile de citire/scriere pe disc.
    Interfata publica intentionat simpla pentru a permite
    inlocuirea backend-ului JSON cu SQLite fara modificari in UI.
    """

    def __init__(self, data_dir: str | None = None):
        self._dir = data_dir or get_data_dir()
        os.makedirs(self._dir, exist_ok=True)
        logger.info("DataManager initializat: %s", self._dir)

    @property
    def data_dir(self) -> str:
        return self._dir

    def _path(self, filename: str) -> str:
        return os.path.join(self._dir, filename)

    # ─── Config si setari ────────────────────────────────────────────────────

    def save(self, filename: str, data) -> bool:
        """Salveaza JSON atomic (write-to-tmp + rename)."""
        path = self._path(filename)
        tmp  = path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            if os.path.exists(path):
                os.remove(path)
            os.rename(tmp, path)
            logger.debug("Salvat: %s", filename)
            return True
        except OSError as e:
            logger.error("Eroare scriere '%s': %s", filename, e)
            try:
                os.remove(tmp)
            except OSError:
                pass
            return False

    def load(self, filename: str, default=None):
        """Incarca JSON. Daca fisierul nu exista, returneaza default."""
        path = self._path(filename)
        if not os.path.exists(path):
            if default is not None:
                self.save(filename, default)
            return copy.deepcopy(default) if default is not None else {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Eroare citire '%s': %s", filename, e)
            return copy.deepcopy(default) if default is not None else {}

    # ─── Log QSO ────────────────────────────────────────────────────────────

    @staticmethod
    def log_filename(contest_id: str) -> str:
        """Returneaza numele fisierului JSON pentru un contest_id."""
        safe_id = re.sub(r'[^a-zA-Z0-9_\-]', '_', contest_id)
        return f"log_{safe_id}.json"

    def load_log(self, contest_id: str) -> list[dict]:
        """Incarca log-ul pentru concursul dat. Returneaza [] daca nu exista."""
        data = self.load(self.log_filename(contest_id), default=[])
        if not isinstance(data, list):
            logger.warning("Log corupt pentru '%s', resetat la []", contest_id)
            return []
        return data

    def save_log(self, contest_id: str, data: list[dict]) -> bool:
        """Salveaza log-ul unui concurs."""
        return self.save(self.log_filename(contest_id), data)

    def list_logs(self) -> list[str]:
        """Returneaza lista de contest_id-uri care au fisiere de log."""
        ids = []
        try:
            for fn in os.listdir(self._dir):
                if fn.startswith("log_") and fn.endswith(".json"):
                    cid = fn[4:-5]  # strip log_ prefix and .json suffix
                    ids.append(cid)
        except OSError:
            pass
        return sorted(ids)

    def append_qso(self, contest_id: str, qso: dict) -> bool:
        """Adauga un QSO in log fara a rescrie tot fisierul (JSON rescrie tot)."""
        log = self.load_log(contest_id)
        log.insert(0, qso)
        return self.save_log(contest_id, log)

    # ─── Backup ─────────────────────────────────────────────────────────────

    def backup(self, contest_id: str, data: list[dict]) -> bool:
        """Creeaza backup timestampat. Pastreaza ultimele 50 de backup-uri."""
        try:
            backup_dir = os.path.join(self._dir, "backups")
            os.makedirs(backup_dir, exist_ok=True)
            ts      = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_id = re.sub(r'[^a-zA-Z0-9_\-]', '_', contest_id)
            filename = f"log_{safe_id}_{ts}.json"
            path = os.path.join(backup_dir, filename)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            # Curata backup-uri vechi (pastreaza max 50)
            pattern = f"log_{safe_id}_*.json"
            backups = sorted(Path(backup_dir).glob(pattern))
            while len(backups) > 50:
                try:
                    backups[0].unlink()
                    backups.pop(0)
                except OSError as e:
                    logger.warning("Nu pot sterge backup vechi: %s", e)
                    break
            logger.info("Backup creat: %s", filename)
            return True
        except OSError as e:
            logger.error("Eroare backup pentru '%s': %s", contest_id, e)
            return False


# ─── Instanta globala ─────────────────────────────────────────────────────────
_dm_instance: DataManager | None = None


def get_dm() -> DataManager:
    """Returneaza instanta singleton DataManager."""
    global _dm_instance
    if _dm_instance is None:
        _dm_instance = DataManager()
    return _dm_instance


def init_dm(data_dir: str) -> DataManager:
    """Initializeaza DataManager cu un director specific (apelat din main.py)."""
    global _dm_instance
    _dm_instance = DataManager(data_dir)
    return _dm_instance
