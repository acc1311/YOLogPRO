#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py - YO Log PRO v19 - Launcher

Structura repo:
  main.py          <- acest fisier
  yolog/           <- pachetul cu tot codul

PyInstaller impacheteaza 'yolog' ca pachet complet.
"""

import sys
import os

_here = os.path.dirname(os.path.abspath(__file__)) if not getattr(sys, 'frozen', False) else None
if _here and _here not in sys.path:
    sys.path.insert(0, _here)

import logging
import logging.handlers
from pathlib import Path


def resource_path(rel: str) -> str:
    """Calea spre resursa bundled in EXE (MEIPASS) sau din surse."""
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS  # type: ignore[attr-defined]
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, rel)


def get_data_dir() -> str:
    """
    Returneaza directorul pentru date (loguri, configuratii).
    - EXE in Program Files  -> %%APPDATA%%\\YO Log PRO
    - EXE portabil / Python -> langa EXE / directorul curent
    """
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        protected = False
        if sys.platform == "win32":
            pf    = os.environ.get("PROGRAMFILES",      r"C:\Program Files").lower()
            pf86  = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)").lower()
            windir = os.environ.get("WINDIR",           r"C:\Windows").lower()
            exe_lower = exe_dir.lower()
            if exe_lower.startswith(pf) or exe_lower.startswith(pf86) or exe_lower.startswith(windir):
                protected = True
        if protected:
            appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
            data_dir = os.path.join(appdata, "YO Log PRO")
            os.makedirs(data_dir, exist_ok=True)
            return data_dir
        return exe_dir
    return os.path.abspath(".")


def setup_logging(data_dir: str) -> None:
    log_dir = Path(data_dir) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter(
        "%(asctime)s %(name)-20s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh = logging.handlers.RotatingFileHandler(
        log_dir / "yolog.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    fh.setLevel(logging.INFO)
    fh.setFormatter(fmt)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.WARNING)
    ch.setFormatter(fmt)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(fh)
    root_logger.addHandler(ch)
    logging.info(
        "YO Log PRO v19 | Python %s | frozen=%s | data_dir=%s",
        sys.version.split()[0], getattr(sys, "frozen", False), data_dir,
    )


def main() -> None:
    data_dir = get_data_dir()
    setup_logging(data_dir)
    logger = logging.getLogger(__name__)

    # DPI awareness Windows
    if sys.platform == "win32":
        try:
            import ctypes
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                ctypes.windll.user32.SetProcessDPIAware()
        except Exception as e:
            logger.warning("DPI fix esuat: %s", e)

    try:
        from yolog.data.manager import init_dm
    except ImportError as e:
        _fatal(f"Nu pot importa DataManager:\n{e}", data_dir)
        return

    dm = init_dm(data_dir)

    try:
        cfg  = dm.load("config.json", default={})
        lang = cfg.get("lang", "ro")
        from yolog import i18n
        i18n.set_lang(lang)
    except Exception as e:
        logger.warning("Eroare initializare limba: %s", e)

    try:
        from yolog.ui.app import App
        app = App(dm=dm, data_dir=data_dir)
        app.mainloop()
    except Exception as e:
        logger.exception("Eroare fatala in App.mainloop: %s", e)
        _fatal(str(e), data_dir)


def _fatal(msg: str, data_dir: str = "") -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "YO Log PRO - Eroare",
            f"Aplicatia nu a putut porni:\n\n{msg}"
            + (f"\n\nLog: {data_dir}\\logs\\yolog.log" if data_dir else ""),
        )
        root.destroy()
    except Exception:
        print(f"EROARE FATALA: {msg}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
