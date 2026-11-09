"""Feria Valencia (web oficial) · ferias abiertas al público en el recinto de Benimàmet.

La página del calendario lista cada feria con su perfil (público o profesional) en las
clases CSS (perfil-publico / perfil-profesional) y las fechas como «26 Dic / 4 Ene» (sin año).
Las ferias de público llenan el recinto y el metro (líneas 2 y 4, parada Fira València).
Las profesionales se guardan como «algo de gente».
"""
from __future__ import annotations

import re
from datetime import date, timedelta

from bs4 import BeautifulSoup

from ..common import Event, clean, fetch, norm, today, tr

SID = "feria"
NAME = "Feria Valencia (calendario oficial)"
URL = "https://www.feriavalencia.com/calendario-proximos-eventos/"
MONTHS = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12}
# Ferias de público que suelen llenar mucho (decenas de miles de visitantes)
BIG = ("expojove", "automovil", "comic", "japan weekend", "joc&rol", "joc & rol", "tattoo", "2 ruedas", "dos ruedas", "42k")
TIP_PUB = ("El metro (líneas 2 y 4, parada Fira València) y los accesos al recinto van llenos, sobre todo por la tarde y el fin de semana.",
           "El metro (línies 2 i 4, parada Fira València) i els accessos al recinte van plens, sobretot per la vesprada i el cap de setmana.",
           "The metro (lines 2 and 4, Fira València stop) and the access roads to the venue are crowded, especially in the afternoon and at weekends.")
TIP_PRO = ("Feria profesional: más tráfico y metro algo más lleno hacia Feria Valencia en horario de entrada y salida.",
           "Fira professional: més trànsit i metro una mica més ple cap a Fira València a l'hora d'entrada i d'eixida.",
           "Trade fair: more traffic and a somewhat busier metro towards Feria Valencia at opening and closing times.")


def _day(txt: str, ref: date) -> date | None:
    m = re.search(r"(\d{1,2})\s+([a-zé]{3})", norm(txt))
    if not m or m.group(2) not in MONTHS:
        return None
    d, mo = int(m.group(1)), MONTHS[m.group(2)]
    # la lista no trae año: el más cercano a partir de hace 2 meses
    for y in (ref.year - 1, ref.year, ref.year + 1):
        try:
            c = date(y, mo, d)
        except ValueError:
            continue
        if c >= ref - timedelta(days=60):
            return c
    return None


def parse(html: str, ref: date | None = None) -> list[Event]:
    ref = ref or today()
    soup = BeautifulSoup(html, "lxml")
    out: list[Event] = []
    for it in soup.select(".e-loop-item.type-evento"):
        cls = it.get("class", [])
        title_el = it.select_one(".elementor-heading-title")
        dates = [x.get_text(" ", strip=True) for x in it.select(".elementor-post-info__item")]
        if not title_el or not dates:
            continue
        title = clean(title_el.get_text(" ", strip=True))
        start = _day(dates[0], ref)
        end = _day(dates[-1].lstrip("/ "), start or ref) if len(dates) > 1 else start
        if not start:
            continue
        if not end or end < start or (end - start).days > 20:
            end = start
        public = "perfil-publico" in cls
        link = it.select_one("a[href]")
        url = link["href"] if link and link["href"].startswith("http") else URL
        level = 2 if public else 1
        if public and any(k in norm(title) for k in BIG):
            people = ("decenas de miles de visitantes", "desenes de milers de visitants", "tens of thousands of visitors")
        elif public:
            people = ("miles de visitantes", "milers de visitants", "thousands of visitors")
        else:
            people = ("feria profesional", "fira professional", "trade fair")
        d = start
        while d <= end:
            if d >= ref - timedelta(days=1):
                weekend = d.weekday() >= 5
                lvl = level if (public or not weekend) else 1
                t = (f"Feria Valencia: {title}", f"Fira València: {title}", f"Feria Valencia: {title}")
                out.append(Event(date=d.isoformat(), title=t[0], type="Feria", zones=["feria"], level=lvl,
                                 source_name=NAME, source_url=url, start="10:00", frm="10:00", to="20:30",
                                 people=people[0], tip=(TIP_PUB if public else TIP_PRO)[0], official=True,
                                 approx=True, sid=SID, tags=[] if public else ["profesional"],
                                 i18n=tr(title=t, tip=TIP_PUB if public else TIP_PRO, people=people)))
            d += timedelta(days=1)
    return out


def _group(evs: list[Event]) -> list[Event]:
    """Varias ferias el mismo día y del mismo tipo (público / profesional) -> un solo aviso."""
    groups: dict[tuple, list[Event]] = {}
    for e in evs:
        groups.setdefault((e.date, bool(e.tags)), []).append(e)
    out = []
    for (_, _), g in sorted(groups.items()):
        if len(g) == 1:
            out.append(g[0]); continue
        e = g[0]
        names = [x.title.split(": ", 1)[1] for x in g]
        joined = ", ".join(names[:-1]) + " y " + names[-1]
        joined_va = ", ".join(names[:-1]) + " i " + names[-1]
        joined_en = ", ".join(names[:-1]) + " and " + names[-1]
        e.title = f"Feria Valencia: {joined}"
        e.i18n["va"]["title"] = f"Fira València: {joined_va}"
        e.i18n["en"]["title"] = f"Feria Valencia: {joined_en}"
        e.level = max(x.level for x in g)
        out.append(e)
    return out


def scrape() -> list[Event]:
    evs = _group(parse(fetch(URL, name="feria")))
    if not evs:
        raise RuntimeError("No se encontró ninguna feria en el calendario (¿ha cambiado la web?)")
    return evs
