# -*- coding: utf-8 -*-
"""
data/importer.py — Import log-uri din formate externe
Suportat: ADIF 3.x, CSV, Cabrillo 2.0/3.0
Zero dependențe de UI.
"""
from __future__ import annotations
import re
import csv
import io
import datetime
import logging
from ..core.bands import freq2band, CAB2_MODE_REV

logger = logging.getLogger(__name__)


class Importer:
    """Parsere pentru formate standard de log radio."""

    # ─── ADIF ────────────────────────────────────────────────────────────────

    @staticmethod
    def parse_adif(text: str) -> list[dict]:
        """
        Parsează ADIF 3.x. Returnează lista de QSO-uri ca dict-uri.
        Câmpuri suportate: CALL, BAND, MODE, QSO_DATE, TIME_ON,
                           RST_SENT, RST_RCVD, FREQ, GRIDSQUARE,
                           COMMENT, STX, SRX.
        """
        qsos: list[dict] = []

        # Skip header (tot ce e înainte de <EOH>)
        eoh = text.upper().find("<EOH>")
        if eoh >= 0:
            text = text[eoh + 5:]

        records = re.split(r'<EOR>', text, flags=re.IGNORECASE)
        for rec in records:
            rec = rec.strip()
            if not rec:
                continue

            fields: dict[str, str] = {}
            for m in re.finditer(r'<(\w+):(\d+)(?::[^>]*)?>',
                                  rec, re.IGNORECASE):
                tag    = m.group(1).upper()
                length = int(m.group(2))
                value  = rec[m.end(): m.end() + length]
                fields[tag] = value

            if "CALL" not in fields:
                continue

            q: dict = {
                "c": fields["CALL"].upper(),
                "b": fields.get("BAND", "40m"),
                "m": fields.get("MODE", "SSB"),
                "s": fields.get("RST_SENT", "59"),
                "r": fields.get("RST_RCVD", "59"),
            }

            # Dată
            qd = fields.get("QSO_DATE", "")
            if len(qd) == 8:
                q["d"] = f"{qd[:4]}-{qd[4:6]}-{qd[6:8]}"
            else:
                q["d"] = datetime.datetime.utcnow().strftime("%Y-%m-%d")

            # Oră
            qt = fields.get("TIME_ON", "")
            q["t"] = f"{qt[:2]}:{qt[2:4]}" if len(qt) >= 4 else "00:00"

            # Frecvență (MHz → kHz)
            fr = fields.get("FREQ", "")
            if fr:
                try:
                    fv = float(fr)
                    q["f"] = str(int(round(fv * 1000) if fv < 1000 else fv))
                except ValueError:
                    q["f"] = fr
                    logger.debug("ADIF FREQ invalid: '%s'", fr)
            else:
                q["f"] = ""

            # Notă / Locator
            q["n"]  = fields.get("GRIDSQUARE", fields.get("COMMENT", ""))
            q["ss"] = fields.get("STX", "")
            q["sr"] = fields.get("SRX", "")

            qsos.append(q)

        logger.info("ADIF: importate %d QSO-uri", len(qsos))
        return qsos

    # ─── CSV ─────────────────────────────────────────────────────────────────

    @staticmethod
    def parse_csv(text: str) -> list[dict]:
        """
        Parsează CSV cu header. Coloane așteptate (case-insensitive):
        Call/Callsign, Band, Mode, RST_Sent, RST_Rcvd,
        Date, Time, Freq, Note/Comment, Nr_S, Nr_R
        """
        qsos: list[dict] = []
        try:
            reader = csv.DictReader(io.StringIO(text))
            for row in reader:
                # Normalizăm cheile la lowercase pentru lookup flexibil
                r = {k.lower().strip(): v for k, v in row.items()}

                call = (r.get("call") or r.get("callsign") or "").upper().strip()
                if not call:
                    continue

                qsos.append({
                    "c":  call,
                    "b":  r.get("band") or "40m",
                    "m":  r.get("mode") or "SSB",
                    "s":  r.get("rst_sent") or r.get("rst_s") or "59",
                    "r":  r.get("rst_rcvd") or r.get("rst_r") or "59",
                    "d":  r.get("date") or datetime.datetime.utcnow().strftime("%Y-%m-%d"),
                    "t":  r.get("time") or "00:00",
                    "f":  r.get("freq") or "",
                    "n":  r.get("note") or r.get("comment") or "",
                    "ss": r.get("nr_s") or r.get("ss") or "",
                    "sr": r.get("nr_r") or r.get("sr") or "",
                })
        except csv.Error as e:
            logger.error("CSV parse error: %s", e)

        logger.info("CSV: importate %d QSO-uri", len(qsos))
        return qsos

    # ─── CABRILLO ────────────────────────────────────────────────────────────

    @staticmethod
    def parse_cabrillo(text: str) -> list[dict]:
        """Parsează Cabrillo 2.0 și 3.0. Detectează versiunea automat."""
        qsos: list[dict] = []
        version = "3.0"

        for line in text.strip().splitlines():
            line = line.strip()
            if line.upper().startswith("START-OF-LOG:"):
                version = line.split(":", 1)[1].strip() or "3.0"
            if not line.upper().startswith("QSO:"):
                continue
            parts = line[4:].strip()
            if version.startswith("2"):
                q = Importer._parse_cab2_qso(parts)
            else:
                q = Importer._parse_cab3_qso(parts)
            if q:
                qsos.append(q)

        logger.info("Cabrillo %s: importate %d QSO-uri", version, len(qsos))
        return qsos

    @staticmethod
    def _parse_cab2_qso(parts: str) -> dict | None:
        """Parsează o linie QSO Cabrillo 2.0."""
        try:
            tokens = parts.split()
            if len(tokens) < 8:
                return None
            call = tokens[7] if len(tokens) > 7 else ""
            if not call or call == "--":
                return None

            d = tokens[2]
            if "-" not in d and len(d) == 8:
                d = f"{d[:4]}-{d[4:6]}-{d[6:8]}"

            t = tokens[3]
            t = f"{t[:2]}:{t[2:4]}" if len(t) >= 4 else t

            return {
                "c":  call.upper(),
                "b":  freq2band(tokens[0]) or "40m",
                "m":  CAB2_MODE_REV.get(tokens[1].upper(), "SSB"),
                "s":  tokens[5] if len(tokens) > 5 else "59",
                "r":  tokens[8] if len(tokens) > 8 else "59",
                "d":  d, "t": t, "f": tokens[0],
                "n":  tokens[9] if len(tokens) > 9 and tokens[9] != "--" else "",
                "ss": tokens[6] if len(tokens) > 6 and tokens[6] != "--" else "",
                "sr": tokens[9] if len(tokens) > 9 and tokens[9] != "--" else "",
            }
        except (IndexError, ValueError) as e:
            logger.debug("Cabrillo 2.0 QSO parse error: %s | linie: '%s'", e, parts)
            return None

    @staticmethod
    def _parse_cab3_qso(parts: str) -> dict | None:
        """Parsează o linie QSO Cabrillo 3.0."""
        try:
            tokens = parts.split()
            if len(tokens) < 7:
                return None
            call = tokens[7] if len(tokens) > 7 else ""
            if not call:
                return None

            d = tokens[2]
            if "-" not in d and len(d) == 8:
                d = f"{d[:4]}-{d[4:6]}-{d[6:8]}"

            t = tokens[3]
            t = f"{t[:2]}:{t[2:4]}" if len(t) >= 4 else t

            return {
                "c":  call.upper(),
                "b":  freq2band(tokens[0]) or "40m",
                "m":  tokens[1].upper(),
                "s":  tokens[5] if len(tokens) > 5 else "59",
                "r":  tokens[8] if len(tokens) > 8 else "59",
                "d":  d, "t": t, "f": tokens[0],
                "n":  tokens[9] if len(tokens) > 9 else "",
                "ss": tokens[6] if len(tokens) > 6 else "",
                "sr": tokens[9] if len(tokens) > 9 else "",
            }
        except (IndexError, ValueError) as e:
            logger.debug("Cabrillo 3.0 QSO parse error: %s | linie: '%s'", e, parts)
            return None