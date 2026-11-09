"""Cruceros en el puerto de València · días con varios barcos.

Fuente: CruiseTimetables (horarios de escalas que publican las navieras). No es una web
oficial del puerto, así que los eventos se marcan como «no oficial». Un solo barco apenas
se nota; con varios barcos el mismo día (miles de turistas) se llena el centro histórico.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

from bs4 import BeautifulSoup

from ..common import Event, clean, fetch, shift, today, tr

SID = "cruceros"
NAME = "CruiseTimetables (escalas de cruceros en València)"
URL = "https://www.cruisetimetables.com/valenciaspainschedule-{m}{y}.html"
MON = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
MIN_PAX = 4500     # por debajo, apenas se nota en la ciudad
BIG_PAX = 8000     # muchísimos turistas
ZONES = ["mercado", "reina", "ayuntamiento", "carmen"]
TIP = ("Los cruceristas visitan sobre todo el Mercado Central, la Lonja, la Catedral y la Plaza de la Reina, entre las 10:00 y las 16:00. Mejor ir a primera hora o por la tarde.",
       "Els creueristes visiten sobretot el Mercat Central, la Llotja, la Catedral i la plaça de la Reina, entre les 10:00 i les 16:00. Millor anar a primera hora o per la vesprada.",
       "Cruise passengers mostly visit the Central Market, the Silk Exchange, the Cathedral and Plaza de la Reina, between 10:00 and 16:00. Better to go early or late in the afternoon.")


def _hhmm(s: str) -> str:
    return f"{s[:2]}:{s[2:]}" if s and len(s) == 4 else ""


def parse_month(html: str, year: int, month: int) -> dict[date, list[dict]]:
    soup = BeautifulSoup(html, "lxml")
    days: dict[date, list[dict]] = {}
    for it in soup.select(".psovde-listing"):
        day_el, ship_el = it.select_one(".psovde-day"), it.select_one(".psovde-ship")
        pax_el, times_el = it.select_one(".psovde-passengers"), it.select_one(".psovde-times")
        if not (day_el and ship_el and pax_el):
            continue
        m = re.search(r"\b(\d{1,2})\b", day_el.get_text(" ", strip=True))
        pax = re.sub(r"\D", "", pax_el.get_text())
        if not m or not pax:
            continue
        try:
            d = date(year, month, int(m.group(1)))
        except ValueError:
            continue
        times = clean(times_el.get_text(" ", strip=True)) if times_el else ""
        a = re.search(r"a\s*(\d{4})", times)
        dep = re.search(r"d\s*(\d{4})", times)
        days.setdefault(d, []).append({"ship": clean(ship_el.get_text(" ", strip=True)), "pax": int(pax),
                                       "arr": _hhmm(a.group(1)) if a else "", "dep": _hhmm(dep.group(1)) if dep else ""})
    return days


def scrape(months: int = 3) -> list[Event]:
    t = today()
    out: list[Event] = []
    ok = 0
    for i in range(months):
        y, mo = t.year + (t.month - 1 + i) // 12, (t.month - 1 + i) % 12 + 1
        url = URL.format(m=MON[mo - 1], y=y)
        try:
            html = fetch(url, name=f"cruceros_{y}{mo:02d}", tries=2)
        except Exception:  # noqa: BLE001  (los meses lejanos a veces aún no existen)
            if i == 0:
                raise
            continue
        ok += 1
        for d, ships in sorted(parse_month(html, y, mo).items()):
            pax = sum(s["pax"] for s in ships)
            if d < t - timedelta(days=1) or len(ships) < 2 or pax < MIN_PAX:
                continue
            arr = min((s["arr"] for s in ships if s["arr"]), default="08:00")
            dep = max((s["dep"] for s in ships if s["dep"]), default="18:00")
            frm, to = shift(arr, 90), shift(dep, -90)
            if to <= frm:
                frm, to = "10:00", "16:00"
            n = len(ships)
            names = ", ".join(s["ship"] for s in ships)
            title = (f"{n} cruceros en el puerto (unos {pax:,} turistas)".replace(",", "."),
                     f"{n} creuers al port (uns {pax:,} turistes)".replace(",", "."),
                     f"{n} cruise ships in port (about {pax:,} tourists)")
            people = (f"unos {pax:,} cruceristas ({names})".replace(",", "."),
                      f"uns {pax:,} creueristes ({names})".replace(",", "."),
                      f"about {pax:,} cruise passengers ({names})")
            out.append(Event(date=d.isoformat(), title=title[0], type="Turismo", zones=ZONES,
                             level=2 if pax >= BIG_PAX else 1, source_name=NAME, source_url=url,
                             start=frm, frm=frm, to=to, people=people[0], tip=TIP[0], official=False,
                             approx=True, sid=SID, i18n=tr(title=title, tip=TIP, people=people)))
    if not ok:
        raise RuntimeError("No se pudo leer el calendario de cruceros")
    return out
