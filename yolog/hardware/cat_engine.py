# -*- coding: utf-8 -*-
"""
hardware/cat_engine.py — Motor CAT bidirecțional
Suportat: Yaesu CAT, Icom CI-V, Kenwood CAT, Elecraft CAT, Hamlib/rigctld

FUNCȚIONALITĂȚI:
  • Citire/scriere frecvență și mod (polling la interval configurabil)
  • PTT via CAT (protocol nativ) sau via RTS/DTR pe port serial
  • Split/VFO-B — setare frecvență VFO secundar
  • S-meter — citire nivel semnal (Icom, Kenwood, Hamlib; Yaesu parțial)
  • Auto-start rigctld pentru Hamlib

ZERO import tkinter. Thread-safe prin Queue.
UI-ul primește update-uri exclusiv prin callback-ul on_update,
care trebuie apelat prin queue.Queue + tk.after() din App.
"""
from __future__ import annotations
import threading
import socket
import time
import logging
import subprocess
import sys
import os

logger = logging.getLogger(__name__)

# ─── Pyserial opțional ───────────────────────────────────────────────────────
try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False
    logger.info("pyserial nu este instalat — CAT serial dezactivat")

# ─── Mapări mod ──────────────────────────────────────────────────────────────
YAESU_MODE_MAP: dict[bytes, str] = {
    b'\x00': "LSB", b'\x01': "USB", b'\x02': "CW", b'\x03': "CW",
    b'\x04': "AM",  b'\x08': "FM",  b'\x0a': "DIGI", b'\x0c': "DIGI",
    b'\x0e': "FT8",
}
YAESU_MODE_REV: dict[str, int] = {
    "LSB": 0x00, "USB": 0x01, "CW": 0x02, "AM": 0x04,
    "FM": 0x08, "SSB": 0x01, "DIGI": 0x0a, "RTTY": 0x0a,
    "FT8": 0x0e, "FT4": 0x0e,
}
ICOM_MODE_MAP: dict[int, str] = {
    0x00: "LSB", 0x01: "USB", 0x02: "AM", 0x03: "CW",
    0x04: "RTTY", 0x05: "FM", 0x06: "CW", 0x07: "DIGI",
    0x08: "FT8", 0x11: "FT8",
}
ICOM_MODE_REV: dict[str, int] = {
    "LSB": 0x00, "USB": 0x01, "AM": 0x02, "CW": 0x03,
    "RTTY": 0x04, "FM": 0x05, "DIGI": 0x07, "FT8": 0x08,
    "FT4": 0x08, "SSB": 0x01,
}
KENWOOD_MODE_REV: dict[str, str] = {
    "LSB": "1", "USB": "2", "SSB": "2", "CW": "3",
    "FM": "4", "AM": "5", "RTTY": "6", "DIGI": "9",
    "FT8": "9", "FT4": "9",
}
HAMLIB_MODE_MAP: dict[str, str] = {
    "USB": "USB", "LSB": "LSB", "CW": "CW", "CWR": "CW",
    "FM": "FM", "AM": "AM", "RTTY": "RTTY", "RTTYR": "RTTY",
    "PKTUSB": "FT8", "PKTLSB": "DIGI",
    "FT8": "FT8", "FT4": "FT4", "DIGI": "DIGI", "DATA": "DIGI",
}
HAMLIB_MODE_REV: dict[str, str] = {
    "SSB": "USB", "USB": "USB", "LSB": "LSB", "CW": "CW",
    "FM": "FM", "AM": "AM", "RTTY": "RTTY",
    "DIGI": "PKTUSB", "FT8": "PKTUSB", "FT4": "PKTUSB",
}

CAT_BAUD_DEFAULTS: dict[str, int] = {
    "Yaesu CAT":       38400, "Icom CI-V":     19200,
    "Kenwood CAT":      9600, "Elecraft CAT":  38400,
    "Ten-Tec":          1200, "Alinco DX":     9600,
    "Yaesu FT-847":     4800, "Yaesu FT-100":  4800,
    "Icom CI-V Lent":   1200,
    "Hamlib/rigctld":   4532,
}

# Parametri seriali impliciți per protocol (data_bits, parity, stop_bits)
CAT_SERIAL_DEFAULTS: dict[str, tuple] = {
    "Yaesu CAT":       (8, "N", 2),
    "Icom CI-V":       (8, "N", 1),
    "Kenwood CAT":     (8, "N", 1),
    "Elecraft CAT":    (8, "N", 2),
    "Ten-Tec":         (8, "N", 2),
    "Alinco DX":       (8, "N", 1),
    "Yaesu FT-847":    (8, "N", 2),
    "Yaesu FT-100":    (8, "N", 2),
    "Icom CI-V Lent":  (8, "N", 1),
    "Hamlib/rigctld":  (8, "N", 1),
}

CAT_PROTOCOLS = [
    "Yaesu CAT", "Icom CI-V", "Kenwood CAT",
    "Elecraft CAT", "Ten-Tec", "Alinco DX",
    "Yaesu FT-847", "Yaesu FT-100", "Icom CI-V Lent",
    "Hamlib/rigctld", "Manual (fără CAT)",
]

# Grupare protocoale pentru UI (afișare separatoare)
CAT_PROTOCOL_GROUPS = {
    "Yaesu": ["Yaesu CAT", "Yaesu FT-847", "Yaesu FT-100"],
    "Icom":  ["Icom CI-V", "Icom CI-V Lent"],
    "Kenwood / Elecraft": ["Kenwood CAT", "Elecraft CAT"],
    "Alte radio": ["Ten-Tec", "Alinco DX"],
    "Software": ["Hamlib/rigctld", "Manual (fără CAT)"],
}

# Metode PTT disponibile
PTT_METHODS = ["CAT", "RTS", "DTR", "None"]

POLL_INTERVAL_DEFAULT = 2.0   # secunde între poll-uri (fallback dacă nu e în cfg)


class CATEngine:
    """
    Motor CAT bidirecțional — polling configurabil, thread separat.

    Funcționalități noi față de v1:
      • ptt_on() / ptt_off()      — PTT via CAT, RTS sau DTR
      • set_split_freq(khz)       — setare frecvență VFO-B (split)
      • get_smeter() -> int|None  — nivel semnal 0-100 (% S-meter)
      • poll_interval             — interval poll din cfg (cat_poll_sec)

    Utilizare corectă (thread-safe cu Tkinter):
        import queue
        cat_queue = queue.Queue()
        cat = CATEngine(on_update=cat_queue.put)
        cat.connect(cfg)

        # În App.__init__:
        def _process_cat_queue(self):
            try:
                while True:
                    freq, mode = self._cat_queue.get_nowait()
                    self._apply_cat_update(freq, mode)
            except queue.Empty:
                pass
            self.after(200, self._process_cat_queue)
    """

    def __init__(self, on_update=None):
        """
        Args:
            on_update: callable(freq_khz: str, mode: str) — apelat din thread poll.
                       ATENȚIE: nu apelați widget-uri Tkinter direct din acesta.
                       Folosiți queue.Queue ca intermediar.
        """
        self._ser      = None      # serial.Serial — CAT
        self._ptt_ser  = None      # serial.Serial — PTT (port separat, opțional)
        self._sock     = None      # socket Hamlib
        self._thread   = None
        self._stop     = threading.Event()
        self._lock     = threading.Lock()
        self.connected    = False
        self.protocol     = "Manual (fără CAT)"
        self.ptt_method   = "CAT"   # CAT / RTS / DTR / None
        self.last_freq    = ""
        self.last_mode    = ""
        self.last_error   = ""
        self.last_smeter  = None    # int 0-100 sau None
        self.on_update    = on_update
        self.poll_interval = POLL_INTERVAL_DEFAULT
        # CI-V address implicit 0x94 (IC-7300/IC-7610).
        # Adrese comune: IC-735=0x04, IC-746=0x56, IC-756=0x50,
        #                IC-7000=0x70, IC-7300=0x94, IC-7610=0x98
        self.civ_addr  = 0x94

    # ─── Conectare ───────────────────────────────────────────────────────────

    def connect(self, cfg: dict) -> tuple[bool, str]:
        """Conectează la radio conform configurației. Returns (success, message)."""
        self.disconnect()
        self.protocol = cfg.get("cat_protocol", "Manual (fără CAT)")
        self.ptt_method = cfg.get("cat_ptt_method", "CAT")
        try:
            self.poll_interval = float(cfg.get("cat_poll_sec", POLL_INTERVAL_DEFAULT))
            if self.poll_interval < 0.5:
                self.poll_interval = 0.5
        except (ValueError, TypeError):
            self.poll_interval = POLL_INTERVAL_DEFAULT

        if self.protocol == "Manual (fără CAT)":
            # Chiar și în modul manual, PTT RTS/DTR se poate folosi
            if self.ptt_method in ("RTS", "DTR"):
                self._open_ptt_port(cfg)
            return True, "Manual — CAT dezactivat"

        if self.protocol == "Hamlib/rigctld":
            ok, msg = self._connect_hamlib(cfg)
        else:
            ok, msg = self._connect_serial(cfg)

        # Dacă CAT e OK și PTT e RTS/DTR pe port separat, deschide și PTT
        if ok and self.ptt_method in ("RTS", "DTR"):
            ptt_port = cfg.get("cat_ptt_port", "")
            if ptt_port and ptt_port != cfg.get("cat_port", ""):
                self._open_ptt_port(cfg)

        return ok, msg

    def _open_ptt_port(self, cfg: dict):
        """Deschide port serial separat doar pentru PTT (RTS/DTR)."""
        if not HAS_SERIAL:
            return
        ptt_port = cfg.get("cat_ptt_port", "") or cfg.get("cat_port", "")
        if not ptt_port:
            return
        # Dacă PTT e pe același port ca CAT, folosim self._ser direct
        if ptt_port == cfg.get("cat_port", "") and self._ser:
            return
        try:
            self._ptt_ser = serial.Serial(
                port=ptt_port, baudrate=9600,
                bytesize=8, parity="N", stopbits=1,
                timeout=0.1
            )
            self._ptt_ser.rts = False
            self._ptt_ser.dtr = False
            logger.info("PTT port deschis: %s", ptt_port)
        except serial.SerialException as e:
            logger.warning("Nu pot deschide PTT port %s: %s", ptt_port, e)
            self._ptt_ser = None

    def _connect_serial(self, cfg: dict) -> tuple[bool, str]:
        if not HAS_SERIAL:
            return False, "pyserial nu este instalat!\nInstalează: pip install pyserial"

        port = cfg.get("cat_port", "")
        if not port:
            return False, "Port COM neselectat!"

        baud = int(cfg.get("cat_baud", CAT_BAUD_DEFAULTS.get(self.protocol, 9600)))

        try:
            civ_hex = cfg.get("cat_civaddr", "94")
            self.civ_addr = int(civ_hex, 16) if civ_hex else 0x94
        except ValueError:
            self.civ_addr = 0x94
            logger.warning("cat_civaddr invalid '%s', folosit 0x94", civ_hex)

        defaults = CAT_SERIAL_DEFAULTS.get(self.protocol, (8, "N", 2))
        try:
            data_bits = int(cfg.get("cat_databits", defaults[0]))
            parity    = cfg.get("cat_parity", defaults[1]).upper()[:1] or "N"
            stop_bits = float(cfg.get("cat_stopbits", defaults[2]))
        except (ValueError, TypeError):
            data_bits, parity, stop_bits = defaults

        try:
            self._ser = serial.Serial(
                port=port, baudrate=baud,
                bytesize=data_bits, parity=parity, stopbits=stop_bits,
                timeout=0.5, write_timeout=1.0,
            )
            # Asigurăm că RTS/DTR nu activează PTT la conectare
            self._ser.rts = False
            self._ser.dtr = False
            self.connected = True
            self.last_error = ""
            self._start_poll_thread()
            logger.info("CAT conectat serial: %s @ %d baud", port, baud)
            return True, f"Conectat: {port} @ {baud} baud"
        except serial.SerialException as e:
            self.connected = False
            self.last_error = str(e)
            logger.error("CAT serial connect error: %s", e)
            return False, f"Eroare port serial:\n{e}"

    # ─── Hamlib rigctld auto-start ───────────────────────────────────────────

    _rigctld_proc: "subprocess.Popen | None" = None

    @staticmethod
    def _find_rigctld() -> str | None:
        """Caută rigctld.exe în: lângă EXE (PyInstaller), lângă script, PATH."""
        candidates = []
        if getattr(sys, "frozen", False):
            base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
            candidates.append(os.path.join(base, "rigctld.exe"))
            candidates.append(os.path.join(os.path.dirname(sys.executable), "rigctld.exe"))
        here = os.path.dirname(os.path.abspath(__file__))
        for rel in ["rigctld.exe",
                    "../../hamlib/rigctld.exe",
                    "../../rigctld.exe",
                    "../../../hamlib/bin/rigctld.exe"]:
            candidates.append(os.path.normpath(os.path.join(here, rel)))
        main_dir = os.path.dirname(sys.argv[0]) if sys.argv else "."
        candidates.append(os.path.join(main_dir, "rigctld.exe"))
        candidates.append(os.path.join(main_dir, "hamlib", "rigctld.exe"))
        for c in candidates:
            if os.path.isfile(c):
                logger.info("rigctld găsit: %s", c)
                return c
        import shutil
        found = shutil.which("rigctld") or shutil.which("rigctld.exe")
        if found:
            logger.info("rigctld în PATH: %s", found)
            return found
        return None

    def _start_rigctld(self, cfg: dict, port: int) -> tuple[bool, str]:
        try:
            test = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test.settimeout(0.5)
            test.connect(("localhost", port))
            test.close()
            logger.info("rigctld deja rulează pe port %d", port)
            return True, f"rigctld deja activ pe port {port}"
        except (socket.error, OSError):
            pass

        exe = self._find_rigctld()
        if not exe:
            return False, (
                "rigctld.exe nu a fost găsit!\n\n"
                "Plasează rigctld.exe în același folder cu YO_Log_PRO.exe\n"
                "sau instalează Hamlib din: https://hamlib.github.io"
            )

        model_id = str(cfg.get("cat_hamlib_model", 3073))
        com_port  = cfg.get("cat_port", "")
        baud      = str(cfg.get("cat_baud", 9600))

        cmd = [exe, "-m", model_id, "-t", str(port), "-v"]
        if com_port and com_port.strip():
            cmd += ["-r", com_port, "-s", baud]

        logger.info("Pornire rigctld: %s", " ".join(cmd))
        try:
            flags = 0
            if sys.platform == "win32":
                flags = subprocess.CREATE_NO_WINDOW
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=flags
            )
            CATEngine._rigctld_proc = proc
            for _ in range(20):
                time.sleep(0.1)
                try:
                    test = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    test.settimeout(0.3)
                    test.connect(("localhost", port))
                    test.close()
                    logger.info("rigctld pornit OK (PID %d)", proc.pid)
                    return True, f"rigctld pornit (PID {proc.pid})"
                except (socket.error, OSError):
                    pass
                if proc.poll() is not None:
                    stderr_out = proc.stderr.read().decode(errors="ignore")[:300]
                    return False, f"rigctld s-a oprit imediat:\n{stderr_out}"
            return False, "rigctld pornit dar nu răspunde pe port (timeout 2s)"
        except Exception as ex:
            logger.error("Eroare pornire rigctld: %s", ex)
            return False, f"Nu pot porni rigctld:\n{ex}"

    def stop_rigctld(self):
        """Oprește procesul rigctld pornit de noi (dacă există)."""
        proc = CATEngine._rigctld_proc
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=3)
                logger.info("rigctld oprit (PID %d)", proc.pid)
            except Exception as ex:
                logger.warning("Eroare oprire rigctld: %s", ex)
            CATEngine._rigctld_proc = None

    def _connect_hamlib(self, cfg: dict) -> tuple[bool, str]:
        host = cfg.get("cat_hamlib_host", "localhost")
        port = int(cfg.get("cat_hamlib_port", 4532))
        if host in ("localhost", "127.0.0.1"):
            ok, msg = self._start_rigctld(cfg, port)
            if not ok:
                self.connected = False
                self.last_error = msg
                return False, msg
            logger.info("rigctld auto-start: %s", msg)
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(3)
            self._sock.connect((host, port))
            self.connected = True
            self.last_error = ""
            self._start_poll_thread()
            logger.info("CAT Hamlib conectat: %s:%d", host, port)
            return True, f"Hamlib conectat: {host}:{port}"
        except (socket.error, OSError) as e:
            self.connected = False
            self.last_error = str(e)
            logger.error("CAT Hamlib connect error: %s", e)
            return False, (f"Eroare conectare Hamlib:\n{e}\n\n"
                           "Verifică: port COM corect, model corect, cablu conectat.")

    def _start_poll_thread(self):
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._poll_loop, daemon=True, name="CAT-poll"
        )
        self._thread.start()

    # ─── Deconectare ─────────────────────────────────────────────────────────

    def disconnect(self):
        """Oprește thread-ul de poll și închide conexiunea."""
        self._stop.set()
        self.connected = False
        time.sleep(0.1)

        with self._lock:
            if self._ser:
                try:
                    # Asigurăm PTT off înainte de închidere
                    self._ser.rts = False
                    self._ser.dtr = False
                    self._ser.close()
                except Exception as e:
                    logger.debug("Eroare închidere serial: %s", e)
                self._ser = None

            if self._ptt_ser:
                try:
                    self._ptt_ser.rts = False
                    self._ptt_ser.dtr = False
                    self._ptt_ser.close()
                except Exception as e:
                    logger.debug("Eroare închidere PTT port: %s", e)
                self._ptt_ser = None

            if self._sock:
                try:
                    self._sock.close()
                except Exception as e:
                    logger.debug("Eroare închidere socket Hamlib: %s", e)
                self._sock = None

        self.last_freq   = ""
        self.last_mode   = ""
        self.last_smeter = None
        logger.info("CAT deconectat")

    # ─── Poll loop ───────────────────────────────────────────────────────────

    def _poll_loop(self):
        """Rulează în thread daemon. Nu atinge niciun widget Tkinter."""
        logger.debug("CAT poll thread pornit (interval %.1fs)", self.poll_interval)
        while not self._stop.is_set():
            try:
                freq, mode = self._read_radio()
                if freq:
                    self.last_freq = freq
                    self.last_mode = mode or self.last_mode
                    if self.on_update:
                        self.on_update(self.last_freq, self.last_mode)
            except Exception as e:
                self.last_error = str(e)
                self.connected = False
                logger.error("CAT poll error (deconectat): %s", e)
                break
            self._stop.wait(self.poll_interval)
        logger.debug("CAT poll thread oprit")

    # ─── Citire frecvență și mod ─────────────────────────────────────────────

    def _read_radio(self) -> tuple[str | None, str | None]:
        if self.protocol == "Yaesu CAT":        return self._yaesu_get()
        if self.protocol in ("Icom CI-V", "Icom CI-V Lent"):
            return self._icom_get()
        if self.protocol in ("Kenwood CAT", "Elecraft CAT",
                              "Ten-Tec", "Alinco DX"):
            return self._kenwood_get()
        if self.protocol in ("Yaesu FT-847", "Yaesu FT-100"):
            return self._yaesu_get()
        if self.protocol == "Hamlib/rigctld":   return self._hamlib_get()
        return None, None

    # ─── YAESU CAT ───────────────────────────────────────────────────────────

    def _yaesu_send(self, cmd: int, p1=0, p2=0, p3=0, p4=0) -> bytes:
        with self._lock:
            if not self._ser:
                return b""
            try:
                self._ser.reset_input_buffer()
                self._ser.write(bytes([p1, p2, p3, p4, cmd]))
                time.sleep(0.05)
                return self._ser.read(self._ser.in_waiting or 1)
            except serial.SerialException as e:
                logger.error("Yaesu send error: %s", e)
                return b""

    def _yaesu_get(self) -> tuple[str | None, str | None]:
        raw = self._yaesu_send(0x03)
        if len(raw) >= 5:
            bcd = ""
            for b in raw[:4]:
                bcd += f"{(b >> 4) & 0xF}{b & 0xF}"
            try:
                hz = int(bcd)
                khz = str(hz // 1000)
                mode = YAESU_MODE_MAP.get(raw[4:5], "SSB")
                return khz, mode
            except ValueError as e:
                logger.debug("Yaesu BCD decode error: %s", e)
        return None, None

    def _yaesu_set_freq(self, khz) -> bool:
        with self._lock:
            if not self._ser:
                return False
            try:
                hz = int(float(khz) * 1000)
                hz_str = f"{hz:08d}"
                b = [(int(hz_str[i]) << 4) | int(hz_str[i + 1])
                     for i in range(0, 8, 2)]
                b.append(0x01)
                self._ser.write(bytes(b))
                return True
            except (serial.SerialException, ValueError) as e:
                logger.error("Yaesu set_freq error: %s", e)
                return False

    def _yaesu_set_mode(self, mode: str) -> bool:
        with self._lock:
            if not self._ser:
                return False
            try:
                mb = YAESU_MODE_REV.get(mode.upper(), 0x01)
                self._ser.write(bytes([mb, 0, 0, 0, 0x07]))
                return True
            except serial.SerialException as e:
                logger.error("Yaesu set_mode error: %s", e)
                return False

    def _yaesu_ptt(self, tx: bool) -> bool:
        """PTT via Yaesu CAT. P4=1=TX, P4=0=RX. Comandă 0x08."""
        with self._lock:
            if not self._ser:
                return False
            try:
                p4 = 0x01 if tx else 0x00
                self._ser.write(bytes([0x00, 0x00, 0x00, p4, 0x08]))
                time.sleep(0.05)
                return True
            except serial.SerialException as e:
                logger.error("Yaesu PTT error: %s", e)
                return False

    def _yaesu_set_split_freq(self, khz) -> bool:
        """
        Selectează VFO-B, setează frecvența, revine la VFO-A.
        Comandă 0x05 cu P4=1 selectează VFO-B pe unele modele Yaesu.
        """
        with self._lock:
            if not self._ser:
                return False
            try:
                # Selectare VFO-B
                self._ser.write(bytes([0x00, 0x00, 0x00, 0x01, 0x05]))
                time.sleep(0.05)
                # Setare frecvență VFO-B
                hz = int(float(khz) * 1000)
                hz_str = f"{hz:08d}"
                b = [(int(hz_str[i]) << 4) | int(hz_str[i + 1])
                     for i in range(0, 8, 2)]
                b.append(0x01)
                self._ser.write(bytes(b))
                time.sleep(0.05)
                # Revenire la VFO-A
                self._ser.write(bytes([0x00, 0x00, 0x00, 0x00, 0x05]))
                time.sleep(0.05)
                return True
            except (serial.SerialException, ValueError) as e:
                logger.error("Yaesu split freq error: %s", e)
                return False

    def _yaesu_smeter(self) -> int | None:
        """
        Citire S-meter Yaesu. Comanda 0xF7 returnează 5 bytes pe FT-8x7/FT-991.
        Byte 0 conține nivelul de semnal brut (0-255).
        Nu toate modelele suportă — returnează None dacă nu răspunde.
        """
        raw = self._yaesu_send(0xF7)
        if len(raw) >= 5:
            try:
                raw_val = raw[0]   # 0x00-0xFF
                # Mapăm la 0-100%: S9 ≈ 0x73 pe FT-817/857
                return min(100, int(raw_val * 100 / 0xFF))
            except Exception:
                pass
        return None

    # ─── ICOM CI-V ───────────────────────────────────────────────────────────

    def _icom_send(self, cmd: int, subcmd: int | None = None, data: bytes = b"") -> bytes:
        with self._lock:
            if not self._ser:
                return b""
            try:
                addr = self.civ_addr
                pkt = bytes([0xFE, 0xFE, addr, 0xE0, cmd])
                if subcmd is not None:
                    pkt += bytes([subcmd])
                pkt += data + bytes([0xFD])
                self._ser.reset_input_buffer()
                self._ser.write(pkt)
                time.sleep(0.08)
                resp = b""
                t0 = time.time()
                while time.time() - t0 < 0.5:
                    chunk = self._ser.read(self._ser.in_waiting or 1)
                    resp += chunk
                    if b'\xfd' in resp:
                        break
                    time.sleep(0.01)
                return resp
            except serial.SerialException as e:
                logger.error("Icom send error: %s", e)
                return b""

    def _icom_bcd_to_hz(self, data: bytes) -> int:
        hz = 0
        for i, b in enumerate(data):
            hz += (b & 0xF) * (10 ** (2 * i))
            hz += ((b >> 4) & 0xF) * (10 ** (2 * i + 1))
        return hz

    def _icom_get(self) -> tuple[str | None, str | None]:
        resp = self._icom_send(0x03)
        idx = resp.find(bytes([0xFE, 0xFE, 0xE0]))
        if idx >= 0:
            frame = resp[idx:]
            if len(frame) >= 11 and frame[4] == 0x03:
                hz = self._icom_bcd_to_hz(frame[5:10])
                khz = str(hz // 1000)
                resp2 = self._icom_send(0x04)
                mode = "SSB"
                idx2 = resp2.find(bytes([0xFE, 0xFE, 0xE0]))
                if idx2 >= 0:
                    f2 = resp2[idx2:]
                    if len(f2) >= 8 and f2[4] == 0x04:
                        mode = ICOM_MODE_MAP.get(f2[5], "SSB")
                return khz, mode
        return None, None

    def _icom_set_freq(self, khz) -> bool:
        with self._lock:
            if not self._ser:
                return False
            try:
                hz = int(float(khz) * 1000)
                bcd = bytes([
                    ((hz // (10 ** (2 * i + 1))) % 10 << 4)
                    | ((hz // (10 ** (2 * i))) % 10)
                    for i in range(5)
                ])
                pkt = (bytes([0xFE, 0xFE, self.civ_addr, 0xE0, 0x05])
                       + bcd + bytes([0xFD]))
                self._ser.reset_input_buffer()
                self._ser.write(pkt)
                time.sleep(0.05)
                return True
            except (serial.SerialException, ValueError) as e:
                logger.error("Icom set_freq error: %s", e)
                return False

    def _icom_set_mode(self, mode: str) -> bool:
        with self._lock:
            if not self._ser:
                return False
            try:
                mb = ICOM_MODE_REV.get(mode.upper(), 0x01)
                self._ser.write(
                    bytes([0xFE, 0xFE, self.civ_addr, 0xE0, 0x06, mb, 0x00, 0xFD])
                )
                return True
            except serial.SerialException as e:
                logger.error("Icom set_mode error: %s", e)
                return False

    def _icom_ptt(self, tx: bool) -> bool:
        """
        PTT via Icom CI-V. Comandă 0x1C, sub-comandă 0x00.
        Data 0x01 = TX, 0x00 = RX. Returnează ACK (0xFB) la succes.
        """
        data = bytes([0x01]) if tx else bytes([0x00])
        resp = self._icom_send(0x1C, subcmd=0x00, data=data)
        # ACK = 0xFB în frame de răspuns
        return b'\xfb' in resp

    def _icom_set_split_freq(self, khz) -> bool:
        """
        Setare frecvență VFO-B pe Icom.
        Comandă 0x07 0x01 = selectare sub-VFO (B), 0x05 = set freq, 0x07 0x00 = revenire VFO-A.
        """
        with self._lock:
            if not self._ser:
                return False
            try:
                # Selectare VFO-B
                pkt_b = bytes([0xFE, 0xFE, self.civ_addr, 0xE0, 0x07, 0x01, 0xFD])
                self._ser.write(pkt_b)
                time.sleep(0.06)
                # Setare frecvență
                hz = int(float(khz) * 1000)
                bcd = bytes([
                    ((hz // (10 ** (2 * i + 1))) % 10 << 4)
                    | ((hz // (10 ** (2 * i))) % 10)
                    for i in range(5)
                ])
                pkt_f = (bytes([0xFE, 0xFE, self.civ_addr, 0xE0, 0x05])
                         + bcd + bytes([0xFD]))
                self._ser.write(pkt_f)
                time.sleep(0.06)
                # Revenire VFO-A
                pkt_a = bytes([0xFE, 0xFE, self.civ_addr, 0xE0, 0x07, 0x00, 0xFD])
                self._ser.write(pkt_a)
                time.sleep(0.05)
                return True
            except (serial.SerialException, ValueError) as e:
                logger.error("Icom split freq error: %s", e)
                return False

    def _icom_smeter(self) -> int | None:
        """
        Citire S-meter Icom. Comandă 0x15, sub-comandă 0x02.
        Răspuns: 2 bytes BCD în frame — 0x0000..0x0255 mapat la S0..S9+60dB.
        S9 = 0x0120 (120 în zecimal), max = 0x0241 (241).
        """
        resp = self._icom_send(0x15, subcmd=0x02)
        idx = resp.find(bytes([0xFE, 0xFE, 0xE0]))
        if idx >= 0:
            frame = resp[idx:]
            # Frame: FE FE E0 addr 15 02 lo hi FD
            if len(frame) >= 9 and frame[4] == 0x15 and frame[5] == 0x02:
                lo = frame[6]
                hi = frame[7]
                raw = (hi & 0x0F) * 100 + ((lo >> 4) & 0x0F) * 10 + (lo & 0x0F)
                # 0=S0, 120=S9, 241=S9+60dB → mapat la 0-100%
                pct = min(100, int(raw * 100 / 241))
                return pct
        return None

    # ─── KENWOOD CAT ─────────────────────────────────────────────────────────

    def _kenwood_cmd(self, cmd: str) -> str:
        with self._lock:
            if not self._ser:
                return ""
            try:
                self._ser.reset_input_buffer()
                self._ser.write((cmd + ";").encode())
                time.sleep(0.05)
                resp = b""
                t0 = time.time()
                while time.time() - t0 < 0.5:
                    chunk = self._ser.read(self._ser.in_waiting or 1)
                    resp += chunk
                    if b";" in resp:
                        break
                    time.sleep(0.01)
                return resp.decode(errors="ignore")
            except serial.SerialException as e:
                logger.error("Kenwood cmd error: %s", e)
                return ""

    def _kenwood_get(self) -> tuple[str | None, str | None]:
        resp = self._kenwood_cmd("FA")
        if resp.startswith("FA") and len(resp) >= 13:
            try:
                hz = int(resp[2:13])
                khz = str(hz // 1000)
                resp2 = self._kenwood_cmd("MD")
                mode = "SSB"
                if resp2.startswith("MD") and len(resp2) >= 3:
                    km = {"1": "LSB", "2": "USB", "3": "CW", "4": "FM",
                          "5": "AM", "6": "RTTY", "7": "CW", "9": "DIGI"}
                    mode = km.get(resp2[2], "SSB")
                return khz, mode
            except ValueError as e:
                logger.debug("Kenwood parse error: %s", e)
        return None, None

    def _kenwood_set_freq(self, khz) -> bool:
        with self._lock:
            if not self._ser:
                return False
            try:
                hz = int(float(khz) * 1000)
                self._ser.write(f"FA{hz:011d};".encode())
                return True
            except (serial.SerialException, ValueError) as e:
                logger.error("Kenwood set_freq error: %s", e)
                return False

    def _kenwood_set_mode(self, mode: str) -> bool:
        with self._lock:
            if not self._ser:
                return False
            try:
                mc = KENWOOD_MODE_REV.get(mode.upper(), "2")
                self._ser.write(f"MD{mc};".encode())
                return True
            except serial.SerialException as e:
                logger.error("Kenwood set_mode error: %s", e)
                return False

    def _kenwood_ptt(self, tx: bool) -> bool:
        """PTT via Kenwood CAT. TX; = transmisie, RX; = recepție."""
        cmd = "TX" if tx else "RX"
        resp = self._kenwood_cmd(cmd)
        # Kenwood răspunde cu `;` la success sau poate rămâne silențios
        return True   # majority of Kenwood rigs don't send explicit ACK

    def _kenwood_set_split_freq(self, khz) -> bool:
        """Setare frecvență VFO-B Kenwood. Comandă FB{freq11cifre};"""
        with self._lock:
            if not self._ser:
                return False
            try:
                hz = int(float(khz) * 1000)
                self._ser.write(f"FB{hz:011d};".encode())
                return True
            except (serial.SerialException, ValueError) as e:
                logger.error("Kenwood split freq error: %s", e)
                return False

    def _kenwood_smeter(self) -> int | None:
        """
        Citire S-meter Kenwood. Comandă SM0; → SM00000; unde bytes 2-6 = 0-30.
        0 = S0, 9 = S9, 15 = S9+20dB, 30 = S9+60dB.
        """
        resp = self._kenwood_cmd("SM0")
        if resp.startswith("SM") and len(resp) >= 7:
            try:
                raw = int(resp[2:7])    # 0-30
                pct = min(100, int(raw * 100 / 30))
                return pct
            except ValueError:
                pass
        return None

    # ─── HAMLIB / rigctld ────────────────────────────────────────────────────

    def _hamlib_cmd(self, cmd: str) -> str:
        try:
            if not self._sock:
                return ""
            self._sock.settimeout(2)
            self._sock.sendall((cmd + "\n").encode())
            resp = b""
            t0 = time.time()
            while time.time() - t0 < 2:
                try:
                    chunk = self._sock.recv(256)
                    if not chunk:
                        break
                    resp += chunk
                    if b"RPRT" in resp or resp.count(b"\n") >= 2:
                        break
                except socket.timeout:
                    break
            return resp.decode(errors="ignore").strip()
        except (socket.error, OSError) as e:
            self.connected = False
            self.last_error = str(e)
            logger.error("Hamlib cmd error: %s", e)
            return ""

    def _hamlib_get(self) -> tuple[str | None, str | None]:
        resp = self._hamlib_cmd("f")
        freq_khz = None
        for line in resp.splitlines():
            line = line.strip()
            if line and not line.startswith("RPRT") and line.isdigit():
                freq_khz = str(int(line) // 1000)
                break
        mode = None
        resp2 = self._hamlib_cmd("m")
        for line in resp2.splitlines():
            line = line.strip()
            if line and not line.startswith("RPRT"):
                mode = HAMLIB_MODE_MAP.get(line.upper(), line.upper())
                break
        return freq_khz, mode

    def _hamlib_set_freq(self, khz) -> bool:
        hz = int(float(khz) * 1000)
        resp = self._hamlib_cmd(f"F {hz}")
        return "RPRT 0" in resp or resp == ""

    def _hamlib_set_mode(self, mode: str) -> bool:
        hm = HAMLIB_MODE_REV.get(mode.upper(), "USB")
        resp = self._hamlib_cmd(f"M {hm} 0")
        return "RPRT 0" in resp or resp == ""

    def _hamlib_ptt(self, tx: bool) -> bool:
        """PTT via Hamlib. T 1 = TX, T 0 = RX."""
        resp = self._hamlib_cmd("T 1" if tx else "T 0")
        return "RPRT 0" in resp or resp == ""

    def _hamlib_set_split_freq(self, khz) -> bool:
        """
        Setare frecvență split via Hamlib.
        Selectăm VFO-B, setăm frecvența, revenim la VFO-A.
        """
        hz = int(float(khz) * 1000)
        # Selectare VFOB
        resp1 = self._hamlib_cmd("V VFOB")
        if "RPRT" in resp1 and "RPRT 0" not in resp1:
            return False
        # Setare frecvență pe VFOB
        resp2 = self._hamlib_cmd(f"F {hz}")
        if "RPRT" in resp2 and "RPRT 0" not in resp2:
            return False
        # Revenire VFOA
        self._hamlib_cmd("V VFOA")
        return True

    def _hamlib_smeter(self) -> int | None:
        """
        Citire S-meter via Hamlib. Comandă 'l STRENGTH' → nivel în dBm.
        Mapăm: -127 dBm = S0 (0%), -73 dBm = S9 (60%), -13 dBm = S9+60dB (100%).
        """
        resp = self._hamlib_cmd("l STRENGTH")
        for line in resp.splitlines():
            line = line.strip()
            if line and not line.startswith("RPRT"):
                try:
                    dbm = float(line)
                    # −127..−13 → 0..100%
                    pct = int((dbm - (-127)) * 100 / ((-13) - (-127)))
                    return max(0, min(100, pct))
                except ValueError:
                    pass
        return None

    # ─── PTT RTS / DTR ───────────────────────────────────────────────────────

    def _get_ptt_ser(self):
        """Returnează portul serial pentru PTT (separat sau cel CAT)."""
        if self._ptt_ser:
            return self._ptt_ser
        return self._ser   # folosim portul CAT dacă nu e separat

    def _ptt_rts(self, tx: bool) -> bool:
        """Activare/dezactivare PTT prin linia RTS a portului serial."""
        with self._lock:
            ser = self._get_ptt_ser()
            if not ser:
                return False
            try:
                ser.rts = tx
                logger.debug("PTT RTS -> %s", tx)
                return True
            except Exception as e:
                logger.error("PTT RTS error: %s", e)
                return False

    def _ptt_dtr(self, tx: bool) -> bool:
        """Activare/dezactivare PTT prin linia DTR a portului serial."""
        with self._lock:
            ser = self._get_ptt_ser()
            if not ser:
                return False
            try:
                ser.dtr = tx
                logger.debug("PTT DTR -> %s", tx)
                return True
            except Exception as e:
                logger.error("PTT DTR error: %s", e)
                return False

    def _ptt_cat(self, tx: bool) -> bool:
        """PTT via protocol CAT nativ al radio-ului."""
        if self.protocol == "Yaesu CAT":              return self._yaesu_ptt(tx)
        if self.protocol in ("Yaesu FT-847",
                             "Yaesu FT-100"):         return self._yaesu_ptt(tx)
        if self.protocol in ("Icom CI-V",
                             "Icom CI-V Lent"):       return self._icom_ptt(tx)
        if self.protocol in ("Kenwood CAT",
                             "Elecraft CAT",
                             "Ten-Tec",
                             "Alinco DX"):            return self._kenwood_ptt(tx)
        if self.protocol == "Hamlib/rigctld":         return self._hamlib_ptt(tx)
        return False

    # ─── API PUBLIC ───────────────────────────────────────────────────────────

    def set_freq(self, khz) -> bool:
        """Trimite frecvență spre radio. Returns True dacă succesul e confirmat."""
        if not self.connected:
            return False
        try:
            if self.protocol == "Yaesu CAT":                return self._yaesu_set_freq(khz)
            if self.protocol in ("Yaesu FT-847",
                                 "Yaesu FT-100"):           return self._yaesu_set_freq(khz)
            if self.protocol in ("Icom CI-V",
                                 "Icom CI-V Lent"):         return self._icom_set_freq(khz)
            if self.protocol in ("Kenwood CAT",
                                 "Elecraft CAT",
                                 "Ten-Tec",
                                 "Alinco DX"):              return self._kenwood_set_freq(khz)
            if self.protocol == "Hamlib/rigctld":           return self._hamlib_set_freq(khz)
        except Exception as e:
            logger.error("set_freq(%s) error: %s", khz, e)
        return False

    def set_mode(self, mode: str) -> bool:
        """Trimite mod spre radio. Returns True dacă succesul e confirmat."""
        if not self.connected:
            return False
        try:
            if self.protocol == "Yaesu CAT":                return self._yaesu_set_mode(mode)
            if self.protocol in ("Yaesu FT-847",
                                 "Yaesu FT-100"):           return self._yaesu_set_mode(mode)
            if self.protocol in ("Icom CI-V",
                                 "Icom CI-V Lent"):         return self._icom_set_mode(mode)
            if self.protocol in ("Kenwood CAT",
                                 "Elecraft CAT",
                                 "Ten-Tec",
                                 "Alinco DX"):              return self._kenwood_set_mode(mode)
            if self.protocol == "Hamlib/rigctld":           return self._hamlib_set_mode(mode)
        except Exception as e:
            logger.error("set_mode(%s) error: %s", mode, e)
        return False

    def ptt_on(self) -> bool:
        """
        Activează PTT (TX). Metoda e determinată de cfg['cat_ptt_method']:
          CAT  → comandă nativă protocol radio
          RTS  → linia RTS a portului serial
          DTR  → linia DTR a portului serial
          None → nu face nimic (returnează False)
        """
        if self.ptt_method == "CAT":
            if not self.connected:
                return False
            return self._ptt_cat(True)
        elif self.ptt_method == "RTS":
            return self._ptt_rts(True)
        elif self.ptt_method == "DTR":
            return self._ptt_dtr(True)
        return False

    def ptt_off(self) -> bool:
        """Dezactivează PTT (RX). Metoda identică cu ptt_on()."""
        if self.ptt_method == "CAT":
            if not self.connected:
                return False
            return self._ptt_cat(False)
        elif self.ptt_method == "RTS":
            return self._ptt_rts(False)
        elif self.ptt_method == "DTR":
            return self._ptt_dtr(False)
        return False

    def set_split_freq(self, khz) -> bool:
        """
        Setează frecvența pe VFO-B (split DX).
        Radio-ul rămâne pe VFO-A după apel.
        Returns True la succes.
        """
        if not self.connected:
            return False
        try:
            if self.protocol == "Yaesu CAT":                return self._yaesu_set_split_freq(khz)
            if self.protocol in ("Yaesu FT-847",
                                 "Yaesu FT-100"):           return self._yaesu_set_split_freq(khz)
            if self.protocol in ("Icom CI-V",
                                 "Icom CI-V Lent"):         return self._icom_set_split_freq(khz)
            if self.protocol in ("Kenwood CAT",
                                 "Elecraft CAT",
                                 "Ten-Tec",
                                 "Alinco DX"):              return self._kenwood_set_split_freq(khz)
            if self.protocol == "Hamlib/rigctld":           return self._hamlib_set_split_freq(khz)
        except Exception as e:
            logger.error("set_split_freq(%s) error: %s", khz, e)
        return False

    def get_smeter(self) -> int | None:
        """
        Citește S-meter-ul radio-ului.
        Returns: int 0-100 (procentaj) sau None dacă nu e suportat.
          0%   = S0
          60%  ≈ S9
          100% = S9+60dB
        """
        if not self.connected:
            return None
        try:
            if self.protocol in ("Icom CI-V", "Icom CI-V Lent"):
                return self._icom_smeter()
            if self.protocol in ("Kenwood CAT", "Elecraft CAT",
                                  "Ten-Tec", "Alinco DX"):
                return self._kenwood_smeter()
            if self.protocol == "Hamlib/rigctld":
                return self._hamlib_smeter()
            if self.protocol in ("Yaesu CAT", "Yaesu FT-847", "Yaesu FT-100"):
                return self._yaesu_smeter()
        except Exception as e:
            logger.error("get_smeter() error: %s", e)
        return None

    @staticmethod
    def list_ports() -> list[str]:
        """Returnează lista porturilor COM disponibile."""
        if not HAS_SERIAL:
            return []
        try:
            return [p.device for p in serial.tools.list_ports.comports()]
        except Exception as e:
            logger.error("list_ports error: %s", e)
            return []
