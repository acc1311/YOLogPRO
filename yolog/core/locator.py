# -*- coding: utf-8 -*-
"""
core/locator.py — Calcul Maidenhead Locator
Zero dependențe externe. Testabil independent.
"""
import math
import logging

logger = logging.getLogger(__name__)


class Loc:
    """Conversii și calcule Maidenhead Locator (Grid Square)."""

    @staticmethod
    def to_latlon(loc: str):
        """Convertește locator Maidenhead la (lat, lon). Returnează (None, None) dacă invalid."""
        loc = loc.upper().strip()
        if len(loc) < 4:
            return None, None
        try:
            lon = (ord(loc[0]) - 65) * 20 - 180
            lat = (ord(loc[1]) - 65) * 10 - 90
            lon += int(loc[2]) * 2
            lat += int(loc[3])
            if len(loc) >= 6:
                lon += (ord(loc[4]) - 65) * (2 / 24) + 1 / 24
                lat += (ord(loc[5]) - 65) * (1 / 24) + 0.5 / 24
            else:
                lon += 1.0
                lat += 0.5
            return lat, lon
        except Exception as e:
            logger.debug("to_latlon error pentru '%s': %s", loc, e)
            return None, None

    @staticmethod
    def dist(a: str, b: str) -> float:
        """Distanța în km între două locatoare. Returnează 0 dacă oricare e invalid."""
        la1, lo1 = Loc.to_latlon(a)
        la2, lo2 = Loc.to_latlon(b)
        if None in (la1, lo1, la2, lo2):
            return 0.0
        d1 = math.radians(la2 - la1)
        d2 = math.radians(lo2 - lo1)
        a_ = (math.sin(d1 / 2) ** 2
              + math.cos(math.radians(la1))
              * math.cos(math.radians(la2))
              * math.sin(d2 / 2) ** 2)
        return round(6371.0 * 2 * math.atan2(math.sqrt(a_), math.sqrt(1 - a_)), 1)

    @staticmethod
    def valid(s: str) -> bool:
        """Verifică dacă string-ul este un locator valid de 4 sau 6 caractere."""
        s = s.upper().strip()
        if len(s) == 4:
            return (s[0:2].isalpha() and s[2:4].isdigit()
                    and 'A' <= s[0] <= 'R' and 'A' <= s[1] <= 'R')
        if len(s) == 6:
            return (s[0:2].isalpha() and s[2:4].isdigit() and s[4:6].isalpha()
                    and 'A' <= s[0] <= 'R' and 'A' <= s[1] <= 'R'
                    and 'A' <= s[4] <= 'X' and 'A' <= s[5] <= 'X')
        return False
