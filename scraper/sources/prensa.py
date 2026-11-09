"""Prensa (Google News) · manifestaciones, huelgas y cortes en València.

Las manifestaciones casi nunca salen en las fuentes oficiales que se pueden leer
automáticamente (la web del Ayuntamiento bloquea a GitHub y la Delegación del Gobierno
no publica listados). Este módulo lee titulares de noticias y crea avisos «sin confirmar»
cuando encuentra una fecha futura, y la hora y el lugar si los menciona.
"""
from __future__ import annotations

import re
import time
from datetime import date, datetime, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup

from ..common import TZ, Event, clean, fetch, hm, norm, today, window
from ..geo import find_zones

SID = "prensa"
QUERIES = [
    "manifestación València",
    "manifestación Valencia convocada",
    "concentración València plaza",
    "huelga general Valencia manifestación",
    "cortes de tráfico Valencia manifestación",
    "marcha Valencia recorrido calle",
]
RSS = "https://news.google.com/rss/search?q={}+when:10d&hl=es&gl=ES&ceid=ES:es"

MONTHS = {m: i + 1 for i, m in enumerate(["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"])}
DAYS = {"lunes": 0, "martes": 1, "miercoles": 2, "jueves": 3, "viernes": 4, "sabado": 5, "domingo": 6}
KEYWORDS = ["manifestacion", "manifestaciones", "concentracion", "huelga", "marcha", "protesta", "cortes de trafico", "calles cortadas", "movilizacion", "cacerolada", "manifestants", "vaga"]
VALENCIA = ["valencia", "valencia,"]
NOT_CITY = ["comunitat valenciana", "comunidad valenciana"]  # vale si además nombra la ciudad
OTHER_CITIES = ["alicante", "castellon", "elche", "madrid", "barcelona", "sevilla", "zaragoza", "bilbao", "malaga", "murcia", "gandia"]


def _dates(text: str, pub: date) -> list[date]:
    t = norm(text)
    out = []
    for m in re.finditer(r"\b(\d{1,2}) de (" + "|".join(MONTHS) + r")\b", t):
        d, mo = int(m.group(1)), MONTHS[m.group(2)]
        y = pub.year + (1 if mo < pub.month - 6 else 0)
        try:
            out.append(date(y, mo, d))
        except ValueError:
            pass
    for m in re.finditer(r"\b(\d{1,2})-?n\b", t):  # 11N, 25N (noviembre)
        d = int(m.group(1))
        if 1 <= d <= 30 and pub.month in (10, 11):
            out.append(date(pub.year, 11, d))
    for m in re.finditer(r"\b(?:este|el proximo|proximo|el)\s+(" + "|".join(DAYS) + r")\b", t):
        wd = DAYS[m.group(1)]
        delta = (wd - pub.weekday()) % 7
        out.append(pub + timedelta(days=delta or 7 if "proximo" in m.group(0) else delta))
    if re.search(r"\bmanana\b", t):
        out.append(pub + timedelta(days=1))
    if re.search(r"\bhoy\b|\besta tarde\b|\besta manana\b", t):
        out.append(pub)
    return out


def _time(text: str) -> str:
    t = norm(text)
    m = re.search(r"\ba las (\d{1,2}(?:[:.]\d{2})?)\s*(?:h|horas)?\b", t) or re.search(r"\b(\d{1,2}[:.]\d{2})\s*h", t) or re.search(r"\b(\d{1,2})\s*horas\b", t)
    if not m:
        return ""
    v = hm(m.group(1))
    return v if v and 7 <= int(v[:2]) <= 23 else ""


def _items(q: str):
    xml = fetch(RSS.format(quote_plus(q)), timeout=30)
    root = ET.fromstring(xml)
    for it in root.iter("item"):
        title = re.sub(r"\s+-\s+[^-]+$", "", clean(it.findtext("title") or ""))  # quita « - Medio»
        link = it.findtext("link") or ""
        desc = clean(BeautifulSoup(it.findtext("description") or "", "lxml").get_text(" "))
        src = clean(it.findtext("source") or "Prensa")
        try:
            pub = parsedate_to_datetime(it.findtext("pubDate")).astimezone(TZ).date()
        except Exception:  # noqa: BLE001
            pub = today()
        yield title, desc, link, src, pub


def scrape() -> list[Event]:
    t0 = today()
    found: dict[tuple, Event] = {}
    errors = 0
    for q in QUERIES:
        try:
            items = list(_items(q))
        except Exception:  # noqa: BLE001
            errors += 1
            continue
        time.sleep(1)
        for title, desc, link, src, pub in items:
            text = f"{title}. {desc}"
            t = norm(text)
            if not any(k in t for k in KEYWORDS):
                continue
            # tiene que hablar de la ciudad de València, no de otra
            head = norm(title)
            in_city = "valencia" in head or "valencian" in head or find_zones(title)
            if not in_city:
                continue
            if any(c in head for c in OTHER_CITIES) and not find_zones(title):
                continue
            ds = [d for d in _dates(text, pub) if t0 <= d <= t0 + timedelta(days=30)]
            if not ds:
                continue
            d = min(ds)
            strike = "huelga" in t or "vaga" in t
            demo = any(k in t for k in ("manifestacion", "concentracion", "marcha", "movilizacion", "protesta", "manifestants"))
            zones = find_zones(text)
            start = _time(text) if demo or zones else ""
            if strike and not demo and not zones:
                typ = "Huelga"
            else:
                typ = "Manifestación"
            k = (d.isoformat(), typ, tuple(sorted(zones)), start)
            if k in found:
                continue
            frm, to = window(start, 150, before=60, after=30)
            tip = ("Convocatoria publicada en prensa; hora y recorrido pueden cambiar. "
                   "Las manifestaciones suelen cortar calles del centro y pueden ser ruidosas.")
            if typ == "Huelga":
                tip = ("Huelga anunciada en prensa. El transporte público funcionará con servicios mínimos: "
                       "habrá menos metros y autobuses y más gente esperando en paradas y andenes.")
            found[k] = Event(
                date=d.isoformat(), title=re.sub(r"\s+-\s+[^-]+$", "", title)[:140], type=typ, zones=zones,
                level=2, source_name=f"Prensa: {src}", source_url=link, start=start, frm=frm, to=to,
                official=False, confirmed=False, approx=True, sid=SID, tip=tip, raw=desc[:400],
            )
    if errors == len(QUERIES):
        raise RuntimeError("No se pudo leer ninguna búsqueda de noticias")
    # si hay un aviso con lugar y hora para ese día, el genérico sin lugar sobra
    out = list(found.values())
    located = {(e.date, e.type) for e in out if e.zones}
    return [e for e in out if e.zones or (e.date, e.type) not in located or e.type == "Huelga"][:25]
