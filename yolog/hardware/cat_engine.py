# -*- coding: utf-8 -*-
"""
hardware/cat_engine.py — Motor CAT bidirecțional
Suportat: Yaesu CAT, Icom CI-V, Kenwood CAT, Elecraft CAT, Hamlib/rigctld

ZERO import tkinter. Thread-safe prin Queue.
UI-ul primește update-uri exclusiv prin callback-ul on_update,
care trebuie apelat prin queue.Queue + tk.after() din App.
"""
from __future__ import annotations
import threading
import socket
import time
import logging

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

# Parametri seriali impliciți per protocol
# (data_bits, parity, stop_bits)
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
POLL_INTERVAL = 2.0  # secunde între poll-uri


class CATEngine:
    """
    Motor CAT bidirecțional — polling 2s, thread separat.

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
                    self._apply_cat_update(freq, mode)  # acum e în firul UI
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
        self._ser      = None      # serial.Serial
        self._sock     = None      # socket Hamlib
        self._thread   = None
        self._stop     = threading.Event()
        self._lock     = threading.Lock()
        self.connected = False
        self.protocol  = "Manual (fără CAT)"
        self.last_freq = ""
        self.last_mode = ""
        self.last_error = ""
        self.on_update = on_update
        self.civ_addr  = 0x94     # Icom CI-V address

    # ─── Conectare ───────────────────────────────────────────────────────────

    def connect(self, cfg: dict) -> tuple[bool, str]:
        """Conectează la radio conform configurației. Returns (success, message)."""
        self.disconnect()
        self.protocol = cfg.get("cat_protocol", "Manual (fără CAT)")

        if self.protocol == "Manual (fără CAT)":
            return True, "Manual — CAT dezactivat"

        if self.protocol == "Hamlib/rigctld":
            return self._connect_hamlib(cfg)
        return self._connect_serial(cfg)

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

        # Parametri seriali configurabili (cu fallback la default-urile protocolului)
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

    def _connect_hamlib(self, cfg: dict) -> tuple[bool, str]:
        host = cfg.get("cat_hamlib_host", "localhost")
        port = int(cfg.get("cat_hamlib_port", 4532))
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
            return False, (f"Eroare Hamlib:\n{e}\n\n"
                           "Asigură-te că rigctld rulează:\n"
                           "rigctld -m MODEL -r PORT")

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
        time.sleep(0.1)  # dă timp thread-ului să observe _stop

        with self._lock:
            if self._ser:
                try:
                    self._ser.close()
                except Exception as e:
                    logger.debug("Eroare închidere serial: %s", e)
                self._ser = None

            if self._sock:
                try:
                    self._sock.close()
                except Exception as e:
                    logger.debug("Eroare închidere socket Hamlib: %s", e)
                self._sock = None

        self.last_freq = ""
        self.last_mode = ""
        logger.info("CAT deconectat")

    # ─── Poll loop (thread separat) ──────────────────────────────────────────

    def _poll_loop(self):
        """Rulează în thread daemon. Nu atinge niciun widget Tkinter."""
        logger.debug("CAT poll thread pornit")
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
            self._stop.wait(POLL_INTERVAL)
        logger.debug("CAT poll thread oprit")

    # ─── Citire frecvență și mod ─────────────────────────────────────────────

    def _read_radio(self) -> tuple[str | None, str | None]:
        if self.protocol == "Yaesu CAT":        return self._yaesu_get()
        if self.protocol in ("Icom CI-V", "Icom CI-V Lent"):
            return self._icom_get()
        if self.protocol in ("Kenwood CAT", "Elecraft CAT",
                              "Ten-Tec", "Alinco DX"):
            return self._kenwood_get()       # ASCII CAT compatibil
        if self.protocol in ("Yaesu FT-847", "Yaesu FT-100"):
            return self._yaesu_get()         # Protocol FT-8x7 identic FIF-232
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
                self._ser.write(
                    bytes([0xFE, 0xFE, self.civ_addr, 0xE0, 0x05])
                    + bcd + bytes([0xFD])
                )
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

    # ─── ELECRAFT (similar Kenwood) ──────────────────────────────────────────

    def _elecraft_get(self) -> tuple[str | None, str | None]:
        return self._kenwood_get()

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

    # ─── API PUBLIC ───────────────────────────────────────────────────────────

    def set_freq(self, khz) -> bool:
        """Trimite frecvență spre radio. Returns True dacă succesul e confirmat."""
        if not self.connected:
            return False
        try:
            if self.protocol == "Yaesu CAT":      return self._yaesu_set_freq(khz)
            if self.protocol == "Icom CI-V":      return self._icom_set_freq(khz)
            if self.protocol == "Kenwood CAT":    return self._kenwood_set_freq(khz)
            if self.protocol == "Elecraft CAT":   return self._kenwood_set_freq(khz)
            if self.protocol == "Hamlib/rigctld":  return self._hamlib_set_freq(khz)
        except Exception as e:
            logger.error("set_freq(%s) error: %s", khz, e)
        return False

    def set_mode(self, mode: str) -> bool:
        """Trimite mod spre radio. Returns True dacă succesul e confirmat."""
        if not self.connected:
            return False
        try:
            if self.protocol == "Yaesu CAT":      return self._yaesu_set_mode(mode)
            if self.protocol == "Icom CI-V":      return self._icom_set_mode(mode)
            if self.protocol == "Kenwood CAT":    return self._kenwood_set_mode(mode)
            if self.protocol == "Elecraft CAT":   return self._kenwood_set_mode(mode)
            if self.protocol == "Hamlib/rigctld":  return self._hamlib_set_mode(mode)
        except Exception as e:
            logger.error("set_mode(%s) error: %s", mode, e)
        return False

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