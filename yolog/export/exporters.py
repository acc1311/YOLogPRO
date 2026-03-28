# -*- coding: utf-8 -*-
"""
export/exporters.py — Exportatori log-uri radio
Suportat: Cabrillo 3.0, Cabrillo 2.0, ADIF 3.1, CSV, EDI, Text/Print

Zero dependențe de UI. Fiecare exportator returnează un string.
"""
from __future__ import annotations
import csv
import io
import datetime
import logging
from ..core.locator import Loc
from ..core.dxcc import DXCC
from ..core.score import Score
from ..core.bands import BAND_FREQ, CAB2_MODE_MAP

logger = logging.getLogger(__name__)


class CabrilloExporter:
    """Export Cabrillo 3.0 și 2.0."""

    @staticmethod
    def export_v3(log: list[dict], cfg: dict, contest: dict,
                  operator: str = "SINGLE-OP",
                  power: str = "HIGH",
                  date_fmt: str = "with_dash") -> str:
        """
        Generează fișier Cabrillo 3.0.

        Args:
            log:      Lista de QSO-uri
            cfg:      Configurație aplicație (call, loc, op_name etc.)
            contest:  Dict cu regulile concursului
            operator: SINGLE-OP / MULTI-OP / CHECKLOG
            power:    HIGH / LOW / QRP
            date_fmt: 'with_dash' (2024-01-15) sau 'no_dash' (20240115)
        """
        my_call = cfg.get("call", "NOCALL")
        contest_name = (contest.get("cabrillo_name", "")
                        or contest.get("name_en", contest.get("name_ro", "CONTEST")))
        exchange_fmt = contest.get("exchange_format", "none")

        lines = [
            "START-OF-LOG: 3.0",
            f"CONTEST: {contest_name}",
            f"CALLSIGN: {my_call}",
            f"GRID-LOCATOR: {cfg.get('loc', '')}",
            f"CATEGORY-OPERATOR: {operator}",
            "CATEGORY-BAND: ALL",
            f"CATEGORY-POWER: {power}",
            "CATEGORY-MODE: MIXED",
            f"NAME: {cfg.get('op_name', '')}",
            f"ADDRESS: {cfg.get('addr', '')}",
            "SOAPBOX: Logged with YO Log PRO v19",
            f"SOAPBOX: {cfg.get('soapbox', '73 GL')}",
            "CREATED-BY: YO Log PRO v19",
        ]

        for q in log:
            freq = _resolve_freq(q)
            es   = _resolve_exchange_sent(q, exchange_fmt, cfg)
            er   = _resolve_exchange_rcvd(q, "log")
            date = _format_date(q.get("d", ""), date_fmt)
            time = q.get("t", "").replace(":", "")

            lines.append(
                f"QSO: {freq:>6} {q.get('m','SSB'):<5} {date} {time} "
                f"{my_call:<13} {q.get('s','59'):<4} {es:<10} "
                f"{q.get('c',''):<13} {q.get('r','59'):<4} {er}"
            )

        lines.append("END-OF-LOG:")
        return "\n".join(lines)

    @staticmethod
    def export_v2(log: list[dict], cfg: dict, contest: dict,
                  category_num: str = "1",
                  exch_sent: str = "none",
                  exch_rcvd: str = "log",
                  date_fmt: str = "with_dash") -> str:
        """Generează fișier Cabrillo 2.0."""
        my_call = cfg.get("call", "NOCALL")
        contest_name = (contest.get("cabrillo_name", "")
                        or contest.get("name_en", contest.get("name_ro", "CONTEST"))).upper()
        _, _, total = Score.total(log, contest, cfg)

        lines = [
            "START-OF-LOG: 2.0",
            "CREATED BY: YO Log PRO v19",
            f"CONTEST: {contest_name}",
            f"CALLSIGN: {my_call}",
            f"NAME: {cfg.get('op_name', '')}",
            f"CATEGORY: {category_num}",
            f"CLAIMED-SCORE: {total}",
            f"ADDRESS: {cfg.get('addr', '')}",
            f"EMAIL: {cfg.get('email', '')}",
            "SOAPBOX: Logged with YO Log PRO v19",
            f"SOAPBOX: {cfg.get('soapbox', '73 GL')}",
        ]

        for q in log:
            freq = _resolve_freq(q)
            mode = CAB2_MODE_MAP.get(q.get("m", "SSB"), "PH")
            date = _format_date(q.get("d", ""), date_fmt)
            time = q.get("t", "").replace(":", "")[:4]
            es   = _resolve_exchange_sent(q, exch_sent, cfg)
            er   = _resolve_exchange_rcvd(q, exch_rcvd)

            lines.append(
                f"QSO: {freq} {mode} {date} {time} "
                f"{my_call:<13} {q.get('s','59'):>2}  {es:<2} "
                f"{q.get('c',''):<13} {q.get('r','59'):>2}  {er:<2}"
            )

        lines.append("END-OF-LOG:")
        return "\n".join(lines)


class ADIFExporter:
    """Export ADIF 3.1."""

    @staticmethod
    def export(log: list[dict], cfg: dict) -> str:
        """Generează fișier ADIF 3.1."""
        my_loc = cfg.get("loc", "")
        lines  = [
            "<ADIF_VER:5>3.1.0",
            "<PROGRAMID:14>YO_Log_PRO_v19",
            "<PROGRAMVERSION:5>18.0",
            f"<MY_GRIDSQUARE:{len(my_loc)}>{my_loc}",
            "<EOH>",
        ]

        for q in log:
            dc = q.get("d", "").replace("-", "")
            tc = q.get("t", "").replace(":", "") + "00"
            note = q.get("n", "")

            freq_mhz = ""
            if q.get("f"):
                try:
                    freq_mhz = f"{float(q['f']) / 1000:.4f}"
                except (ValueError, TypeError):
                    pass

            parts = [
                _af("CALL",     q.get("c", "")),
                _af("BAND",     q.get("b", "")),
                _af("MODE",     q.get("m", "")),
                _af("QSO_DATE", dc),
                _af("TIME_ON",  tc),
                _af("RST_SENT", q.get("s", "59")),
                _af("RST_RCVD", q.get("r", "59")),
            ]

            if freq_mhz:
                parts.append(_af("FREQ", freq_mhz))

            # Locator sau comentariu în notă
            if note:
                note_upper = note.upper().strip()
                candidate = note_upper[:6] if len(note_upper) >= 6 else note_upper
                if Loc.valid(candidate):
                    parts.append(_af("GRIDSQUARE", note_upper[:6]))
                elif Loc.valid(note_upper[:4]):
                    parts.append(_af("GRIDSQUARE", note_upper[:4]))
                else:
                    parts.append(_af("COMMENT", note))

            if q.get("ss"):
                parts.append(_af("STX", q["ss"]))
            if q.get("sr"):
                parts.append(_af("SRX", q["sr"]))

            parts.append("<EOR>")
            lines.append("".join(p for p in parts if p))

        return "\n".join(lines)


class CSVExporter:
    """Export CSV cu header standard."""

    @staticmethod
    def export(log: list[dict], cfg: dict, contest: dict) -> str:
        """Generează CSV complet cu scor per QSO și țară DXCC."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Nr", "Date", "Time", "Call", "Freq", "Band", "Mode",
            "RST_S", "RST_R", "Nr_S", "Nr_R", "Note", "Country", "Score",
        ])
        for i, q in enumerate(log):
            country, _ = DXCC.lookup(q.get("c", ""))
            writer.writerow([
                len(log) - i,
                q.get("d", ""), q.get("t", ""),
                q.get("c", ""), q.get("f", ""),
                q.get("b", ""), q.get("m", ""),
                q.get("s", ""), q.get("r", ""),
                q.get("ss", ""), q.get("sr", ""),
                q.get("n", ""),
                country if country != "Unknown" else "",
                Score.qso(q, contest, cfg),
            ])
        return output.getvalue()


class EDIExporter:
    """Export EDI (REG1TEST format, VHF contests)."""

    @staticmethod
    def export(log: list[dict], cfg: dict, contest: dict) -> str:
        """Generează fișier EDI (REG1TEST;1)."""
        my_call = cfg.get("call", "NOCALL")
        my_loc  = cfg.get("loc", "")
        contest_name = (contest.get("cabrillo_name", "")
                        or contest.get("name_en", "VHF"))
        now = datetime.datetime.utcnow()

        lines = [
            "[REG1TEST;1]",
            f"TName={contest_name}",
            f"TDate={now.strftime('%y%m%d')};{now.strftime('%y%m%d')}",
            f"PCall={my_call}",
            f"PWWLo={my_loc}",
            "PExch=",
            f"PAdr1={cfg.get('addr', '')}",
            "PBand=144",
            "PSect=",
            "[Remarks]",
            "Logged with YO Log PRO v19",
            "[QSORecords]",
        ]

        for q in log:
            dt  = q.get("d", "").replace("-", "")[2:]  # YYMMDD
            tm  = q.get("t", "").replace(":", "")[:4]   # HHMM
            loc = q.get("n", "")
            km  = int(Loc.dist(my_loc, loc)) if my_loc and Loc.valid(loc) else 0

            lines.append(
                f"{dt};{tm};{q.get('c','')};1;"
                f"{q.get('s','59')};{q.get('ss','')};"
                f"{q.get('r','59')};{q.get('sr','')};"
                f"{loc};{km}"
            )

        return "\n".join(lines)


class PrintExporter:
    """Export text formatat pentru printare."""

    @staticmethod
    def export(log: list[dict], cfg: dict, contest: dict) -> str:
        """Generează un raport text de 90 caractere lățime."""
        my_call = cfg.get("call", "NOCALL")
        contest_name = contest.get("name_ro", contest.get("name_en", "?"))

        lines = [
            "=" * 90,
            f"YO Log PRO v19 — {my_call} — {contest_name}",
            f"Generated: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC",
            "=" * 90,
            (f"{'Nr':<4} {'Call':<13} {'Freq':<8} {'Band':<6} {'Mode':<6} "
             f"{'RSTt':<5} {'RSTr':<5} {'Note':<10} {'Country':<15} "
             f"{'Date':<11} {'Time':<6} {'Pts':<5}"),
            "-" * 90,
        ]

        for i, q in enumerate(log):
            country, _ = DXCC.lookup(q.get("c", ""))
            lines.append(
                f"{len(log)-i:<4} {q.get('c',''):<13} {q.get('f',''):<8} "
                f"{q.get('b',''):<6} {q.get('m',''):<6} "
                f"{q.get('s',''):<5} {q.get('r',''):<5} "
                f"{q.get('n',''):<10} {country[:14]:<15} "
                f"{q.get('d',''):<11} {q.get('t',''):<6} "
                f"{Score.qso(q, contest, cfg):<5}"
            )

        qso_pts, mult_count, total = Score.total(log, contest, cfg)
        lines.extend([
            "=" * 90,
            f"Total QSO: {len(log)}  |  Score: {qso_pts}×{mult_count}={total}",
        ])
        return "\n".join(lines)


# ─── Funcții ajutătoare private ──────────────────────────────────────────────

def _af(tag: str, val: str) -> str:
    """Formatează un câmp ADIF: <TAG:LEN>VALUE"""
    if not val:
        return ""
    return f"<{tag}:{len(str(val))}>{val}"


def _resolve_freq(q: dict) -> str:
    """Returnează frecvența ca string int de la QSO sau din BAND_FREQ."""
    freq = q.get("f", "") or str(BAND_FREQ.get(q.get("b", ""), 0))
    try:
        return str(int(float(freq)))
    except (ValueError, TypeError):
        return freq


def _format_date(d: str, fmt: str) -> str:
    """Formatează data pentru Cabrillo."""
    d_raw = d.replace("-", "")
    if len(d_raw) == 8:
        if fmt == "with_dash":
            return f"{d_raw[:4]}-{d_raw[4:6]}-{d_raw[6:8]}"
        return d_raw
    return d


def _resolve_exchange_sent(q: dict, mode: str, cfg: dict) -> str:
    """Rezolvă exchange-ul trimis conform modului."""
    if mode == "county":
        return cfg.get("jud", q.get("n", "--"))
    if mode == "grid":
        return cfg.get("loc", q.get("n", "--"))
    if mode == "serial":
        return q.get("ss", "--")
    return "--"


def _resolve_exchange_rcvd(q: dict, mode: str) -> str:
    """Rezolvă exchange-ul primit."""
    if mode == "log":
        return q.get("sr") or q.get("n") or "--"
    return "--"