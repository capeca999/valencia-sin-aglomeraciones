"""Visit València (Fundació Visit València, Ayuntamiento) · calendario del Valencia Basket.

Formato de cada línea:
  "12/11/2026 a las 20:30 h: Valencia Basket - FC Bayern Múnich. EuroLeague Masculina"
"""
from __future__ import annotations

import re
from datetime import date

from bs4 import BeautifulSoup

from ..common import Event, clean, fetch, hm, in_range, today, window

SID = "visitvalencia"
NAME = "Visit València (Ayuntamiento)"
URL = "https://www.visitvalencia.com/agenda-valencia/partidos-del-valencia-basket-liga-endesa-y-euroliga-en-roig-arena"
LINE = re.compile(r"(\d{2})/(\d{2})/(\d{4})\s+a las\s+(\d{1,2}[:.]\d{2})\s*h?\s*:?\s*(.+?)\.\s*((?:Liga|EuroLeague|Euroliga|Copa|Supercopa|Playoff)[^\n]*)", re.I)


def scrape() -> list[Event]:
    html = fetch(URL, name=SID)
    soup = BeautifulSoup(html, "lxml")
    for s in soup(["script", "style", "noscript"]):
        s.decompose()
    for t in soup.find_all(["strong", "b", "em", "i", "span", "a"]):
        t.unwrap()
    soup = BeautifulSoup(str(soup), "lxml")  # junta los trozos de texto que quedan separados
    text = "\n".join(clean(x) for x in soup.get_text("\n").split("\n"))
    text = re.sub(r"\n(?!\d{2}/\d{2}/\d{4})", " ", text)  # une líneas partidas por negritas
    events = []
    for m in LINE.finditer(text):
        d = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        if not in_range(d) or d < today():
            continue
        start = hm(m.group(4))
        match, comp = clean(m.group(5)), clean(m.group(6))
        women = "femenina" in comp.lower() or "women" in comp.lower() or "valencia bc" in match.lower()
        frm, to = window(start, 120)
        events.append(Event(
            date=d.isoformat(), title=f"{match} ({comp})", type="Baloncesto", zones=["roig"],
            level=1 if women else 2, source_name=NAME, source_url=URL, start=start, frm=frm, to=to,
            people="unos miles de personas" if women else "unas 12.000 personas", sid=SID,
            tip="Evita el entorno del Roig Arena y el transporte hacia Quatre Carreres en esa franja.",
        ))
    return events
