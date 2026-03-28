# -*- coding: utf-8 -*-
"""
core/dxcc.py — Baza de date DXCC + loader cty.dat
Zero dependențe externe. Testabil independent.
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

# Baza de date built-in de prefixe DXCC
_BUILTIN_DB: dict[str, str] = {
    "YO": "Romania", "YP": "Romania", "YQ": "Romania", "YR": "Romania",
    "DL": "Germany", "DJ": "Germany", "DK": "Germany", "DA": "Germany",
    "DB": "Germany", "DC": "Germany", "DD": "Germany", "DF": "Germany",
    "DG": "Germany", "DH": "Germany", "DM": "Germany",
    "G": "England", "M": "England", "2E": "England",
    "GW": "Wales", "GM": "Scotland", "GI": "N. Ireland",
    "GD": "Isle of Man", "GJ": "Jersey", "GU": "Guernsey",
    "F": "France", "TM": "France",
    "HB9": "Switzerland", "HB": "Switzerland",
    "I": "Italy", "IK": "Italy", "IZ": "Italy", "IW": "Italy", "IN3": "Italy",
    "EA": "Spain", "EB": "Spain", "EC": "Spain", "EE": "Spain",
    "CT": "Portugal", "CS": "Portugal", "CU": "Azores",
    "SP": "Poland", "SQ": "Poland", "SN": "Poland", "SO": "Poland", "3Z": "Poland",
    "HA": "Hungary", "HG": "Hungary",
    "OK": "Czech Rep.", "OL": "Czech Rep.",
    "OM": "Slovak Rep.",
    "LZ": "Bulgaria",
    "UR": "Ukraine", "US": "Ukraine", "UT": "Ukraine", "UX": "Ukraine", "UY": "Ukraine",
    "UA": "Russia", "RU": "Russia", "RV": "Russia", "RW": "Russia", "RA": "Russia",
    "OE": "Austria",
    "ON": "Belgium", "OO": "Belgium", "OR": "Belgium", "OT": "Belgium",
    "PA": "Netherlands", "PB": "Netherlands", "PD": "Netherlands", "PE": "Netherlands",
    "OZ": "Denmark", "OU": "Denmark", "5Q": "Denmark",
    "SM": "Sweden", "SA": "Sweden", "SB": "Sweden", "SK": "Sweden",
    "LA": "Norway", "LB": "Norway", "LC": "Norway",
    "OH": "Finland", "OF": "Finland", "OG": "Finland", "OI": "Finland",
    "ES": "Estonia", "YL": "Latvia", "LY": "Lithuania",
    "9A": "Croatia", "S5": "Slovenia", "E7": "Bosnia",
    "Z3": "N. Macedonia", "Z6": "Kosovo", "ZA": "Albania",
    "SV": "Greece", "SW": "Greece", "SX": "Greece", "SY": "Greece",
    "TA": "Turkey", "TC": "Turkey", "YM": "Turkey",
    "4X": "Israel", "4Z": "Israel",
    "SU": "Egypt", "CN": "Morocco", "7X": "Algeria", "3V": "Tunisia",
    "ZS": "South Africa", "ZR": "South Africa", "ZU": "South Africa",
    "W": "USA", "K": "USA", "N": "USA",
    "AA": "USA", "AB": "USA", "AC": "USA", "AD": "USA", "AE": "USA",
    "AF": "USA", "AG": "USA", "AI": "USA", "AK": "USA",
    "KH6": "Hawaii", "KL7": "Alaska", "KP4": "Puerto Rico",
    "VE": "Canada", "VA": "Canada", "VY": "Canada", "VO": "Canada",
    "XE": "Mexico", "XA": "Mexico", "4A": "Mexico",
    "PY": "Brazil", "PP": "Brazil", "PR": "Brazil", "PS": "Brazil",
    "PT": "Brazil", "PU": "Brazil",
    "LU": "Argentina", "LW": "Argentina", "LO": "Argentina",
    "CE": "Chile", "CA": "Chile", "XQ": "Chile",
    "JA": "Japan", "JH": "Japan", "JR": "Japan", "JE": "Japan",
    "JF": "Japan", "JG": "Japan", "JI": "Japan", "JJ": "Japan",
    "JK": "Japan", "JL": "Japan",
    "BY": "China", "BA": "China", "BD": "China", "BG": "China", "BI": "China",
    "HL": "S. Korea", "DS": "S. Korea", "6K": "S. Korea",
    "DU": "Philippines", "DX": "Philippines",
    "HS": "Thailand", "E2": "Thailand",
    "VK": "Australia", "AX": "Australia",
    "ZL": "New Zealand", "ZM": "New Zealand",
    "VU": "India", "AT": "India", "VT": "India",
    "AP": "Pakistan",
    "A4": "Oman", "A6": "UAE", "A7": "Qatar", "A9": "Bahrain",
    "9K": "Kuwait", "HZ": "Saudi Arabia", "7Z": "Saudi Arabia",
    "EK": "Armenia", "4J": "Azerbaijan", "4L": "Georgia",
    "UN": "Kazakhstan", "JT": "Mongolia",
    "XV": "Vietnam", "3W": "Vietnam",
    "TF": "Iceland", "JW": "Svalbard", "OX": "Greenland", "OY": "Faroe Is.",
    "T7": "San Marino", "3A": "Monaco", "C3": "Andorra",
    "HV": "Vatican", "9H": "Malta", "5B": "Cyprus", "4O": "Montenegro",
}


class DXCC:
    """Lookup DXCC din indicativ. Suportă baza built-in + cty.dat extern."""

    # Baza activă — poate fi extinsă cu load_cty_dat()
    DB: dict[str, str] = dict(_BUILTIN_DB)

    @staticmethod
    def lookup(call: str) -> tuple[str, str]:
        """
        Caută țara DXCC pentru un indicativ.
        Returnează (country_name, prefix_used).
        """
        call = call.upper().strip().split("/")[0]
        for n in range(min(4, len(call)), 0, -1):
            if call[:n] in DXCC.DB:
                return DXCC.DB[call[:n]], call[:n]
        if call and call[0] in DXCC.DB:
            return DXCC.DB[call[0]], call[0]
        prefix = call[:2] if len(call) >= 2 else call
        return "Unknown", prefix

    @staticmethod
    def prefix(call: str) -> str:
        """Returnează doar prefixul DXCC pentru un indicativ."""
        return DXCC.lookup(call)[1]

    @staticmethod
    def load_cty_dat(filepath: str) -> tuple[bool, str]:
        """
        Încarcă cty.dat (BigCTY format) și adaugă prefixele în DXCC.DB.
        Returnează (success, message).
        """
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()

            current_entity = None
            added = 0
            for line in text.splitlines():
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if not line.startswith(' ') and ':' in line:
                    # Linie entitate: Romania:  EU  28  274  E6  20.8 ...
                    parts = [p.strip() for p in line.split(':')]
                    if parts:
                        current_entity = parts[0].strip()
                elif line.startswith(' ') and current_entity:
                    # Linie prefixe: YO,YP,YQ,YR,...
                    prefixes = [p.strip().rstrip(',;').lstrip('=*')
                                for p in line.split(',')]
                    for pfx in prefixes:
                        clean = pfx.split('/')[0].strip()
                        if clean and clean.replace('/', '').replace('-', '').isalnum():
                            DXCC.DB[clean.upper()] = current_entity
                            added += 1

            msg = f"CTY.dat încărcat: {filepath} ({added} prefixe)"
            logger.info(msg)
            return True, msg
        except OSError as e:
            msg = f"Nu pot citi {filepath}: {e}"
            logger.error(msg)
            return False, msg
        except Exception as e:
            msg = f"Eroare parsare cty.dat: {e}"
            logger.exception(msg)
            return False, msg

    @staticmethod
    def reset_to_builtin() -> None:
        """Resetează baza la valorile built-in (util pentru teste)."""
        DXCC.DB = dict(_BUILTIN_DB)