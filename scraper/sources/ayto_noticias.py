"""Ayuntamiento de València · noticias de Movilidad.

Aquí se anuncian los «dispositivos especiales de tráfico» por grandes eventos.
No siempre dicen la fecha del evento en el titular, así que se muestran como
«Avisos oficiales recientes» (no van al mapa).
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..common import clean, fetch, norm, today

SID = "ayto_noticias"
NAME = "Ajuntament de València · Noticias de movilidad"
URLS = [
    "https://www.valencia.es/cas/movilidad/noticias",
    "https://www.valencia.es/web/guest/cas/actualidad/movilidad-y-urbanismo",
]
DMY = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")
KEYS = ["dispositivo", "cortes", "corta", "afecciones", "restring", "manifestac", "maraton", "carrera", "concierto",
        "partido", "desfile", "cabalgata", "fallas", "navidad", "mascleta", "evento", "eclipse", "trafico especial", "peatonaliz"]


def scrape() -> list[dict]:
    items, errors = {}, []
    for i, url in enumerate(URLS):
        try:
            html = fetch(url, name=f"{SID}_{i}")
        except Exception as e:  # noqa: BLE001
            errors.append(str(e))
            continue
        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all("a", href=True):
            title = clean(a.get_text(" "))
            if len(title) < 25 or "/content/" not in a["href"] and "actualidad" not in a["href"]:
                continue
            # la fecha suele estar justo después del enlace
            tail = ""
            for sib in a.find_all_next(string=True, limit=12):
                tail += " " + sib
                if DMY.search(tail):
                    break
            m = DMY.search(tail)
            if not m:
                continue
            d = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            if d < today() - timedelta(days=10) or d > today() + timedelta(days=1):
                continue
            if not any(k in norm(title) for k in KEYS):
                continue
            href = urljoin("https://www.valencia.es", a["href"])
            items.setdefault(norm(title)[:80], {"date": d.isoformat(), "title": title, "url": href, "source": "Ajuntament de València"})
    if errors and not items and len(errors) == len(URLS):
        raise RuntimeError("; ".join(errors))
    return sorted(items.values(), key=lambda x: x["date"], reverse=True)[:12]
