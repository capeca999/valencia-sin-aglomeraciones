"""Ayuntamiento de València · Movilidad · «Incidencias y previsiones».

Es la lista oficial de afecciones al tráfico. Incluye conciertos, partidos, carreras,
desfiles y manifestaciones con sus horas, por ejemplo:
"2026-07-10 23:00:00.0 [SÁBADO 11/07] Concierto Alejandro Sanz en el estadio Ciutat de
València (22:30 a 1:00 h). Atención a las afecciones de tráfico..."
"""
from __future__ import annotations

import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from ..common import Event, TZ, clean, fetch, hm, in_range, norm, window
from ..geo import find_zones

SID = "ayto_movilidad"
NAME = "Ajuntament de València · Movilidad"
URLS = [
    "https://www.valencia.es/cas/movilidad/incidencias-y-previsiones",
    "https://www.valencia.es/val/mobilitat/incidencies-i-previsions",
]

ENTRY = re.compile(r"(\d{4}-\d{2}-\d{2}) (\d{2}):(\d{2}):\d{2}(?:\.\d+)?\s+(.+?)(?=\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}|\Z)", re.S)
BRACKET = re.compile(r"\[\s*(?:[A-Za-zÁÉÍÓÚÀÈÒÇáéíóúàèòç\.]+\s+)?(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\s*\]")
MONTHS = {m: i + 1 for i, m in enumerate(["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"])}
MONTHS.update({m: i + 1 for i, m in enumerate(["gener", "febrer", "marc", "abril", "maig", "juny", "juliol", "agost", "setembre", "octubre", "novembre", "desembre"])})
DAY_MONTH = re.compile(r"\b(\d{1,2}) d[e']\s?(" + "|".join(MONTHS) + r")\b")
RANGE = re.compile(r"(\d{1,2}(?:[:.]\d{2})?)\s*(?:h\s*)?(?:a|-|–|hasta|fins a|fins les)\s*(?:las\s|les\s)?(\d{1,2}(?:[:.]\d{2})?)\s*h?")
AT = re.compile(r"(?:a las|a les|desde las|des de les|a partir de las|a partir de les)\s*(\d{1,2}(?:[:.]\d{2})?)")

# (palabras clave, tipo, nivel, duración aproximada en minutos)
KINDS = [
    (["maraton", "marato"], "Carrera", 3, 420),
    (["manifestacion", "manifestacio", "concentracion", "concentracio", "huelga", "vaga", "protesta"], "Manifestación", 2, 150),
    (["partido", "partit", "futbol", "laliga", "copa del rey"], "Fútbol", 3, 120),
    (["concierto", "concert", "festival"], "Concierto", 2, 180),
    (["mascleta", "castillo", "castell", "crida", "ofrenda", "ofrena", "falles", "fallas", "cabalgata", "cavalcada", "desfile", "desfilada", "procesion", "processo", "batalla de flores", "nit d'albaes", "correfoc"], "Fiesta / desfile", 2, 180),
    (["carrera", "cursa", "media maraton", "mitja marato", "10k", "15k", "5k", "triatlon", "duatlon", "ciclista", "bicicletada", "marcha", "marxa", "volta a peu", "san silvestre", "sant silvestre"], "Carrera", 2, 180),
    (["gay games", "evento", "esdeveniment", "fiesta", "festa", "feria", "fira", "acto", "acte", "celebracion", "espectaculo", "exhibicion"], "Evento", 2, 180),
]
EXCLUDE = ["obras", "obres", "reurbaniz", "renaturaliz", "mantenimiento", "manteniment", "coord. obras", "ciclo integral del agua", "poda", "asfalt"]


def _classify(t: str):
    for kws, typ, lvl, dur in KINDS:
        if any(re.search(r"\b" + re.escape(k), t) for k in kws):
            return typ, lvl, dur
    return None


def _event_date(text: str, stamp: datetime) -> date:
    m = BRACKET.search(text)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), m.group(3)
        year = int(y) + (2000 if y and len(y) == 2 else 0) if y else stamp.year
        if not y and mo < stamp.month - 6:
            year += 1
        return date(year, mo, d)
    m = DAY_MONTH.search(norm(text))
    if m:
        d, mo = int(m.group(1)), MONTHS[m.group(2)]
        year = stamp.year + (1 if mo < stamp.month - 6 else 0)
        return date(year, mo, d)
    return stamp.date()


def parse(html: str, url: str) -> list[Event]:
    soup = BeautifulSoup(html, "lxml")
    for s in soup(["script", "style", "noscript"]):
        s.decompose()
    text = soup.get_text("\n")
    events: list[Event] = []
    for m in ENTRY.finditer(text):
        ymd, hh, mm, body = m.group(1), m.group(2), m.group(3), clean(m.group(4))
        body = re.split(r"\b(Previsiones|Previsions|Incidencias|Incidències)\b", body)[0].strip()
        t = norm(body)
        kind = _classify(t)
        if not kind:
            continue
        if any(x in t for x in EXCLUDE) and kind[1] < 3 and "concierto" not in t and "manifest" not in t:
            continue
        stamp = datetime.fromisoformat(f"{ymd}T{hh}:{mm}:00").replace(tzinfo=ZoneInfo("UTC")).astimezone(TZ)
        try:
            d = _event_date(body, stamp)
        except ValueError:
            d = stamp.date()
        if not in_range(d):
            continue
        typ, lvl, dur = kind
        zones = find_zones(body)
        if typ == "Concierto" and any(z in ("mestalla", "ciutat") for z in zones):
            lvl = 3
        frm = to = start = ""
        r = RANGE.search(body)
        if r:
            frm, to = hm(r.group(1)), hm(r.group(2))
            start = frm
        else:
            a = AT.search(t)
            if a:
                start = hm(a.group(1))
                frm, to = window(start, dur)
        title = BRACKET.sub("", body).strip()
        title = re.split(r"(?<=[a-z0-9\)])\. ", title, maxsplit=1)[0][:140]
        events.append(Event(
            date=d.isoformat(), title=title, type=typ, zones=zones, level=lvl,
            source_name=NAME, source_url=url, start=start, frm=frm, to=to,
            tip="Aviso oficial de afecciones al tráfico del Ayuntamiento." + ("" if zones else " No hemos podido situarlo en el mapa: lee el texto completo."),
            raw=body[:600], sid=SID,
        ))
    return events


def scrape() -> list[Event]:
    out: list[Event] = []
    errors = []
    for i, url in enumerate(URLS):
        try:
            html = fetch(url, name=f"{SID}_{i}")
            out.extend(parse(html, url))
        except Exception as e:  # noqa: BLE001
            errors.append(str(e))
    if errors and not out and len(errors) == len(URLS):
        raise RuntimeError("; ".join(errors))
    # castellano y valenciano dan los mismos avisos: quitar duplicados por fecha + hora + zona
    seen, uniq = set(), []
    for e in out:
        k = (e.date, e.start, tuple(e.zones), e.type)
        if k in seen:
            continue
        seen.add(k)
        uniq.append(e)
    return uniq
