# -*- coding: utf-8 -*-
"""
network/callbook.py — Lookup callbook online
Suportat: radioamator.ro, QRZ.com (pagina publică)

Folosește requests + BeautifulSoup4 — robust la schimbări de layout HTML.
Zero dependențe de UI. Rulează în thread separat, comunică prin callback.

Instalare: pip install requests beautifulsoup4
"""
from __future__ import annotations
import re
import threading
import logging
from ..core.dxcc import DXCC

logger = logging.getLogger(__name__)

# ─── Imports opționale ───────────────────────────────────────────────────────
try:
    import requests
    from bs4 import BeautifulSoup
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    logger.warning(
        "requests/beautifulsoup4 nu sunt instalate.\n"
        "Instalează: pip install requests beautifulsoup4\n"
        "Callbook-ul va folosi fallback urllib."
    )

# ─── Constante ───────────────────────────────────────────────────────────────
TIMEOUT = 12
HEADERS = {
    "User-Agent": "YOLogPRO/17 (+yo8acr@gmail.com)",
    "Accept-Encoding": "gzip, deflate",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ro-RO,ro;q=0.9,en-US;q=0.8",
}

# Mapare label HTML → câmp intern
RADIOAMATOR_LABEL_MAP: dict[str, str] = {
    "indicativ": "call", "callsign": "call",
    "proprietar": "name", "titular": "name", "denumire": "name",
    "localitate": "qth", "oras": "qth", "adresa": "qth", "qth": "qth",
    "judet": "county", "locator": "loc", "grid": "loc",
    "clasa": "class", "categorie": "class",
    "zona itu": "itu", "itu": "itu",
    "zona cq": "cq", "cq": "cq",
    "expir": "expires", "valabil": "expires",
    "email": "email", "dxcc": "dxcc",
}

NOT_FOUND_PATTERNS_RO = re.compile(
    r"(nu a fost gasit|nu a fost găsit|not found|nu exista|nu există|"
    r"indicativ invalid|no result|nu avem date|nu s-a gasit)",
    re.IGNORECASE,
)
NOT_FOUND_PATTERNS_QRZ = re.compile(
    r"(not found|no record|callsign not found|this callsign is not in)",
    re.IGNORECASE,
)
GRID_PATTERN = re.compile(r'\b([A-R]{2}\d{2}[A-X]{2})\b', re.IGNORECASE)
EMAIL_PATTERN = re.compile(r'mailto:([^\s"\'><]{5,60})')


class RadioamatorRO:
    """Lookup pe www.radioamator.ro/call-book/"""

    BASE_URL = "https://www.radioamator.ro/call-book/yocall.php?call={}"

    def lookup(self, call: str) -> tuple[dict, str]:
        """
        Caută indicativul pe radioamator.ro.

        Returns:
            (data_dict, raw_html)
            data_dict conține: call, name, qth, county, loc, class, itu, cq, expires, email, dxcc
            Cheie specială '_error' dacă a eșuat, '_not_found' dacă nu există.
        """
        data = {"call": call.upper(), "source": "radioamator.ro"}
        url  = self.BASE_URL.format(call.upper())

        html = self._fetch(url)
        if html is None:
            return {"call": call, "_error": "Eroare conexiune la radioamator.ro"}, ""

        # Parsare cu BeautifulSoup — robust la schimbări de layout
        if not HAS_REQUESTS:
            return data, html
        soup = BeautifulSoup(html, "html.parser")

        for row in soup.find_all("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            label = cells[0].get_text(separator=" ", strip=True).lower().rstrip(":. ")
            value = cells[1].get_text(separator=" ", strip=True)
            if not value or value in ("-", "—", "N/A"):
                continue
            for keyword, field in RADIOAMATOR_LABEL_MAP.items():
                if keyword in label and field not in data:
                    data[field] = value
                    break

        # Fallback locator din text liber
        if "loc" not in data:
            for m in GRID_PATTERN.finditer(html):
                cand = m.group(1).upper()
                if re.match(r'^[A-R]{2}\d{2}[A-X]{2}$', cand, re.IGNORECASE):
                    data["loc"] = cand
                    break

        # Fallback email din mailto:
        if "email" not in data:
            m = EMAIL_PATTERN.search(html)
            if m:
                data["email"] = m.group(1)

        # DXCC din baza internă dacă nu există pe pagină
        if "dxcc" not in data:
            country, _ = DXCC.lookup(call)
            if country != "Unknown":
                data["dxcc"] = country

        # Detectare "nu a fost găsit"
        if NOT_FOUND_PATTERNS_RO.search(html) and len(data) <= 2:
            data["_not_found"] = True

        return data, html

    def _fetch(self, url: str) -> str | None:
        """Descarcă pagina. Returnează HTML string sau None la eroare."""
        if HAS_REQUESTS:
            return self._fetch_requests(url)
        return self._fetch_urllib(url)

    def _fetch_requests(self, url: str) -> str | None:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
            return resp.text
        except requests.RequestException as e:
            logger.error("radioamator.ro fetch error: %s", e)
            return None

    def _fetch_urllib(self, url: str) -> str | None:
        """Fallback dacă requests nu este instalat."""
        try:
            from urllib.request import urlopen, Request
            import gzip
            req  = Request(url, headers=HEADERS)
            resp = urlopen(req, timeout=TIMEOUT)
            raw  = resp.read()
            try:
                return gzip.decompress(raw).decode("utf-8", errors="ignore")
            except Exception:
                return raw.decode("utf-8", errors="ignore")
        except Exception as e:
            logger.error("radioamator.ro urllib fetch error: %s", e)
            return None


class QRZcom:
    """Lookup pe qrz.com (pagina publică, fără API key)."""

    BASE_URL = "https://www.qrz.com/db/{}"

    def lookup(self, call: str) -> tuple[dict, str]:
        """
        Caută indicativul pe QRZ.com.

        Returns:
            (data_dict, raw_html)
        """
        data = {"call": call.upper(), "source": "QRZ.com"}
        url  = self.BASE_URL.format(call.upper())

        html = self._fetch(url)
        if html is None:
            return {"call": call, "_error": "Eroare conexiune la QRZ.com"}, ""

        soup = BeautifulSoup(html, "html.parser") if HAS_REQUESTS else None

        # Dacă BeautifulSoup disponibil, parsare structurată
        if soup:
            data.update(self._parse_with_soup(soup, html))
        else:
            data.update(self._parse_with_regex(html))

        # DXCC fallback
        if "dxcc" not in data:
            country, _ = DXCC.lookup(call)
            if country != "Unknown":
                data["dxcc"] = country

        # Locator fallback
        if "loc" not in data:
            for m in GRID_PATTERN.finditer(html):
                cand = m.group(1).upper()
                data["loc"] = cand
                break

        if NOT_FOUND_PATTERNS_QRZ.search(html):
            data["_not_found"] = True

        return data, html

    def _parse_with_soup(self, soup, html: str) -> dict:
        """Parsare cu BeautifulSoup — preferată."""
        result: dict = {}

        def find_input(name: str) -> str:
            tag = soup.find("input", {"name": name})
            return tag.get("value", "").strip() if tag else ""

        def find_span(id_: str) -> str:
            tag = soup.find("span", {"id": id_})
            return tag.get_text(strip=True) if tag else ""

        # Câmpuri standard QRZ
        v = find_input("name") or find_input("fname")
        if v: result["name"] = v

        v = find_input("addr2") or find_span("addr2")
        if v: result["qth"] = v

        v = find_input("grid")
        if v and re.match(r'^[A-R]{2}\d{2}[A-X]{2}$', v, re.IGNORECASE):
            result["loc"] = v.upper()

        v = find_input("cqzone")
        if v: result["cq"] = v

        v = find_input("ituzone")
        if v: result["itu"] = v

        v = find_input("class")
        if v: result["class"] = v

        v = find_input("dxcc")
        if v: result["dxcc"] = v

        return result

    def _parse_with_regex(self, html: str) -> dict:
        """Fallback fără BeautifulSoup — mai fragil."""
        result: dict = {}

        def fv(patterns: list[str]) -> str:
            for pat in patterns:
                m = re.search(pat, html, re.IGNORECASE | re.DOTALL)
                if m:
                    v = re.sub(r'<[^>]+>', ' ', m.group(1)).strip()
                    if v and len(v) > 1 and v not in ("-", "—"):
                        return v
            return ""

        v = fv([r'"name"\s+value="([^"]{2,60})"',
                r'<span[^>]*itemprop="name"[^>]*>([^<]{2,60})'])
        if v: result["name"] = v

        v = fv([r'"addr2"\s+value="([^"]{2,80})'])
        if v: result["qth"] = v

        v = fv([r'"grid"\s+value="([A-R]{2}\d{2}[A-Xa-x]{2})"'])
        if v: result["loc"] = v

        v = fv([r'"cqzone"\s+value="(\d+)"'])
        if v: result["cq"] = v

        v = fv([r'"ituzone"\s+value="(\d+)"'])
        if v: result["itu"] = v

        return result

    def _fetch(self, url: str) -> str | None:
        if HAS_REQUESTS:
            try:
                resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
                resp.raise_for_status()
                return resp.text
            except requests.RequestException as e:
                logger.error("QRZ.com fetch error: %s", e)
                return None
        # Fallback urllib
        try:
            from urllib.request import urlopen, Request
            import gzip
            req  = Request(url, headers=HEADERS)
            resp = urlopen(req, timeout=TIMEOUT)
            raw  = resp.read()
            try:
                return gzip.decompress(raw).decode("utf-8", errors="ignore")
            except Exception:
                return raw.decode("utf-8", errors="ignore")
        except Exception as e:
            logger.error("QRZ.com urllib fetch error: %s", e)
            return None


class CallbookService:
    """
    Serviciu unificat de lookup callbook.
    Poate combina mai multe surse cu fallback automat.
    """

    def __init__(self):
        self._radioamator = RadioamatorRO()
        self._qrz         = QRZcom()

    def lookup_async(self, call: str, source: str,
                     on_result, on_error) -> threading.Thread:
        """
        Caută indicativul asincron (thread separat).

        Args:
            call:      Indicativul de căutat
            source:    'radioamator.ro' sau 'QRZ.com'
            on_result: callable(data_dict, html_str) — apelat în thread!
                       Apelantul trebuie să folosească queue sau tk.after()
                       pentru a actualiza UI-ul.
            on_error:  callable(error_str)

        Returns:
            Thread-ul pornit (daemon=True)
        """
        def _run():
            try:
                if source == "radioamator.ro":
                    data, html = self._radioamator.lookup(call)
                else:
                    data, html = self._qrz.lookup(call)
                on_result(data, html)
            except Exception as e:
                logger.exception("Callbook lookup error pentru '%s'", call)
                on_error(str(e))

        t = threading.Thread(target=_run, daemon=True, name=f"callbook-{call}")
        t.start()
        return t