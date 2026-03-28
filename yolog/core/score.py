# -*- coding: utf-8 -*-
"""
core/score.py — Motor de calcul scor concurs
Zero dependente de UI. Testabil cu pytest fara Tkinter.
"""
from __future__ import annotations
import re
import logging
from .locator import Loc
from .dxcc import DXCC

logger = logging.getLogger(__name__)


class Score:
    """Calcul punctaj, multiplicatori, duplicate si validare log."""

    @staticmethod
    def qso(q: dict, rules: dict, cfg: dict | None = None) -> int:
        """
        Calculeaza punctele pentru un singur QSO.

        Args:
            q:     QSO dict cu chei 'c' (call), 'b' (band), 'm' (mode), 'n' (note)
            rules: Dict cu regulile concursului activ
            cfg:   Config aplicatie (necesar pentru 'loc' la scoring distance)

        Returns:
            Numarul de puncte (int >= 0)
        """
        if not rules:
            return 1

        scoring_mode = rules.get("scoring_mode", "none")
        if scoring_mode == "none":
            return 0

        call = q.get("c", "").upper()
        special_scoring = rules.get("special_scoring") or {}

        # Statii cu punctaj special (ex: YO8ACR=5)
        if special_scoring and call in special_scoring:
            try:
                return int(special_scoring[call])
            except (ValueError, TypeError):
                logger.warning("special_scoring invalid pentru '%s'", call)

        if scoring_mode == "per_qso":
            return rules.get("points_per_qso", 1)

        elif scoring_mode == "per_band":
            band_pts = rules.get("band_points") or {}
            default_pts = rules.get("points_per_qso", 1)
            return int(band_pts.get(q.get("b", ""), default_pts))

        elif scoring_mode == "maraton":
            return int((rules.get("special_scoring") or {}).get(call, rules.get("points_per_qso", 1)))

        elif scoring_mode == "distance":
            note = q.get("n", "").strip()
            my_loc = (cfg or {}).get("loc", "")
            if Loc.valid(note) and Loc.valid(my_loc):
                return max(1, int(Loc.dist(my_loc, note)))
            return rules.get("points_per_qso", 1)

        return rules.get("points_per_qso", 1)

    @staticmethod
    def mults(data: list[dict], rules: dict) -> tuple[int, set]:
        """
        Calculeaza multiplicatorii din log.

        Returns:
            (count, set_of_mult_values)
        """
        mult_type = rules.get("multiplier_type", "none")
        if mult_type == "none":
            return 1, set()

        mult_set: set[str] = set()
        for q in data:
            note  = q.get("n", "").upper().strip()
            call  = q.get("c", "").upper()
            band  = q.get("b", "")

            if mult_type == "county":
                for county in (rules.get("county_list") or []):
                    pattern = r'\b' + re.escape(county.upper()) + r'\b'
                    if re.search(pattern, note):
                        mult_set.add(county.upper())
                        break

            elif mult_type == "dxcc":
                mult_set.add(DXCC.prefix(call))

            elif mult_type == "band":
                mult_set.add(band)

            elif mult_type == "grid":
                candidate = note[:4] if len(note) >= 4 else note
                if Loc.valid(candidate):
                    mult_set.add(candidate.upper())

        return max(1, len(mult_set)), mult_set

    @staticmethod
    def total(data: list[dict], rules: dict, cfg: dict | None = None) -> tuple[int, int, int]:
        """
        Calculeaza scorul total al logului.

        Returns:
            (qso_points, mult_count, total_score)
        """
        if not data or not rules:
            return 0, 0, 0
        if rules.get("scoring_mode", "none") == "none":
            return 0, 0, 0

        qso_points = sum(Score.qso(q, rules, cfg) for q in data)
        mult_count, _ = Score.mults(data, rules)

        if rules.get("multiplier_type", "none") != "none":
            return qso_points, mult_count, qso_points * mult_count
        return qso_points, mult_count, qso_points

    @staticmethod
    def is_dup(data: list[dict], call: str, band: str, mode: str,
               edit_idx: int | None = None) -> tuple[bool, int]:
        """
        Verifica daca (call, band, mode) exista deja in log.

        Args:
            edit_idx: Index QSO in editare — este ignorat la verificare

        Returns:
            (is_duplicate, index_of_existing_qso)  — index = -1 daca nu e dup
        """
        call_upper = call.upper()
        for i, q in enumerate(data):
            if edit_idx is not None and i == edit_idx:
                continue
            if (q.get("c", "").upper() == call_upper
                    and q.get("b") == band
                    and q.get("m") == mode):
                return True, i
        return False, -1

    @staticmethod
    def worked_other(data: list[dict], call: str, band: str, mode: str) -> bool:
        """True daca indicativul apare in log pe alta banda sau mod (WB indicator)."""
        call_upper = call.upper()
        for q in data:
            if (q.get("c", "").upper() == call_upper
                    and (q.get("b") != band or q.get("m") != mode)):
                return True
        return False

    @staticmethod
    def is_new_mult(data: list[dict], qso: dict, rules: dict) -> bool:
        """True daca QSO-ul aduce un multiplicator nou fata de log-ul existent."""
        mult_type = rules.get("multiplier_type", "none")
        if mult_type == "none":
            return False

        _, existing_mults = Score.mults(data, rules)
        note = qso.get("n", "").upper().strip()
        call = qso.get("c", "").upper()
        new_mult = None

        if mult_type == "county":
            for county in (rules.get("county_list") or []):
                pattern = r'\b' + re.escape(county.upper()) + r'\b'
                if re.search(pattern, note):
                    new_mult = county.upper()
                    break
        elif mult_type == "dxcc":
            new_mult = DXCC.prefix(call)
        elif mult_type == "band":
            new_mult = qso.get("b", "")
        elif mult_type == "grid":
            candidate = note[:4] if len(note) >= 4 else note
            if Loc.valid(candidate):
                new_mult = candidate.upper()

        return new_mult is not None and new_mult not in existing_mults

    @staticmethod
    def validate(data: list[dict], rules: dict,
                 cfg: dict | None = None) -> tuple[bool, str, int]:
        """
        Valideaza log-ul complet fata de regulile concursului.

        Returns:
            (is_valid, message, total_score)
        """
        if not data:
            return False, "Log gol / Empty log", 0
        if not rules:
            return True, f"OK: {len(data)} QSO", len(data)

        messages: list[str] = []

        # Minim QSO-uri
        min_qso = rules.get("min_qso", 0)
        if min_qso > 0 and len(data) < min_qso:
            messages.append(f"⚠ Min {min_qso} QSO necesari, aveti {len(data)}")

        # Duplicate
        seen: set = set()
        dup_count = 0
        for q in data:
            key = (q.get("c", "").upper(), q.get("b"), q.get("m"))
            if key in seen:
                dup_count += 1
            seen.add(key)
        if dup_count:
            messages.append(f"⚠ {dup_count} duplicate(s)")

        # Statii obligatorii
        required = rules.get("required_stations") or []
        if required:
            calls_in_log = {q.get("c", "").upper() for q in data}
            missing = [r for r in required if r.upper() not in calls_in_log]
            if missing:
                messages.append(f"⚠ Lipsa/Missing: {', '.join(missing)}")

        # Benzi/moduri interzise
        allowed_bands = rules.get("allowed_bands") or []
        allowed_modes = rules.get("allowed_modes") or []
        if allowed_bands:
            illegal_band = sum(1 for q in data if q.get("b") not in allowed_bands)
            if illegal_band:
                messages.append(f"⚠ {illegal_band} QSO pe benzi neautorizate")
        if allowed_modes:
            illegal_mode = sum(1 for q in data if q.get("m") not in allowed_modes)
            if illegal_mode:
                messages.append(f"⚠ {illegal_mode} QSO cu moduri neautorizate")

        if messages:
            return False, "\n".join(messages), 0

        _, _, total = Score.total(data, rules, cfg)
        return True, f"✅ OK! {len(data)} QSO — Scor: {total}", total

    @staticmethod
    def band_summary(data: list[dict]) -> dict[str, int]:
        """Returneaza numarul de QSO-uri per banda."""
        summary: dict[str, int] = {}
        for q in data:
            b = q.get("b", "?")
            summary[b] = summary.get(b, 0) + 1
        return dict(sorted(summary.items()))

    @staticmethod
    def mode_summary(data: list[dict]) -> dict[str, int]:
        """Returneaza numarul de QSO-uri per mod."""
        summary: dict[str, int] = {}
        for q in data:
            m = q.get("m", "?")
            summary[m] = summary.get(m, 0) + 1
        return dict(sorted(summary.items()))

    @staticmethod
    def unique_calls(data: list[dict]) -> int:
        """Numarul de indicative unice in log."""
        return len({q.get("c", "").upper() for q in data if q.get("c")})
