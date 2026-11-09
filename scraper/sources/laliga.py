"""LaLiga (web oficial) · partidos en casa del Valencia CF (Mestalla) y Levante UD (Ciutat de València).

La página es Next.js: los partidos vienen en el JSON de <script id="__NEXT_DATA__">.
Se recorre el JSON buscando objetos con equipo local, visitante y fecha.
"""
from __future__ import annotations

import json
import re
from datetime import datetime

from bs4 import BeautifulSoup

from ..common import TZ, Event, fetch, in_range, norm, today, tr, window

SID = "laliga"
NAME = "LaLiga (web oficial)"
CLUBS = [
    {"slug": "valencia-cf", "match": "valencia", "zone": "mestalla", "stadium": "Mestalla",
     "people": ("hasta 49.000 personas", "fins a 49.000 persones", "up to 49,000 people"),
     "tip": ("Evita Blasco Ibáñez, Av. Aragón, Av. Suecia y el metro de Aragón y Facultats en esa franja.",
             "Evita Blasco Ibáñez, l'Av. d'Aragó, l'Av. de Suècia i el metro d'Aragó i Facultats en eixa franja.",
             "Avoid Blasco Ibáñez, Av. Aragón, Av. Suecia and the Aragó and Facultats metro stations during this time.")},
    {"slug": "levante-ud", "match": "levante", "zone": "ciutat", "stadium": "Ciutat de València",
     "people": ("hasta 26.000 personas", "fins a 26.000 persones", "up to 26,000 people"),
     "tip": ("Evita el entorno del estadio (Orriols, Av. Hermanos Machado) y el metro de Orriols en esa franja.",
             "Evita els voltants de l'estadi (Orriols, Av. Germans Machado) i el metro d'Orriols en eixa franja.",
             "Avoid the area around the stadium (Orriols, Av. Hermanos Machado) and Orriols metro station during this time.")},
]


def _name(team) -> str:
    if isinstance(team, dict):
        for k in ("nickname", "name", "shortname", "short_name", "club_name"):
            if isinstance(team.get(k), str):
                return team[k]
        if isinstance(team.get("club"), dict):
            return _name(team["club"])
    return team if isinstance(team, str) else ""


def _walk(o):
    if isinstance(o, dict):
        yield o
        for v in o.values():
            yield from _walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from _walk(v)


def _matches(data):
    seen = set()
    for d in _walk(data):
        home = d.get("home_team") or d.get("homeTeam") or d.get("home")
        away = d.get("away_team") or d.get("awayTeam") or d.get("away")
        when = d.get("date") or d.get("datetime") or d.get("match_date")
        if not (home and away and isinstance(when, str)):
            continue
        key = (_name(home), _name(away), when)
        if key in seen:
            continue
        seen.add(key)
        comp = ""
        for k in ("competition", "subscription", "tournament"):
            if isinstance(d.get(k), dict):
                comp = d[k].get("name", "")
                break
        unknown = any(bool(v) for k, v in d.items() if isinstance(k, str) and ("unknown" in k.lower() or "tbd" in k.lower() or "to_be" in k.lower()))
        yield key[0], key[1], when, comp, unknown


def _scrape_club(club: dict) -> list[Event]:
    url = f"https://www.laliga.com/clubes/{club['slug']}/proximos-partidos"
    html = fetch(url, name=f"{SID}_{club['slug']}")
    soup = BeautifulSoup(html, "lxml")
    tag = soup.find("script", id="__NEXT_DATA__")
    if not tag or not tag.string:
        raise RuntimeError("La página de LaLiga no trae __NEXT_DATA__")
    data = json.loads(tag.string)
    events = []
    for home, away, when, comp, unknown in _matches(data):
        if club["match"] not in norm(home):
            continue
        try:
            dt = datetime.fromisoformat(when.replace("Z", "+00:00"))
        except ValueError:
            continue
        if (dt.hour, dt.minute) == (0, 0):
            unknown = True  # LaLiga pone 00:00 UTC cuando aún no hay hora
        if dt.tzinfo:
            dt = dt.astimezone(TZ)
        d = dt.date()
        if not in_range(d) or d < today():
            continue
        has_time = not unknown
        start = dt.strftime("%H:%M") if has_time else ""
        frm, to = window(start, 120, before=120, after=60)
        extra = ("", "", "") if has_time else (
            " La hora aún no está anunciada: LaLiga la confirma 2-3 semanas antes y el partido puede moverse un día.",
            " L'hora encara no està anunciada: LaLiga la confirma 2-3 setmanes abans i el partit es pot moure un dia.",
            " Kick-off time not announced yet: LaLiga confirms it 2-3 weeks before and the match may move by a day.")
        tip = tuple(a + b for a, b in zip(club["tip"], extra))
        events.append(Event(
            date=d.isoformat(), title=f"{home} – {away}" + (f" ({comp})" if comp else ""), type="Fútbol",
            zones=[club["zone"]], level=3, source_name=NAME, source_url=url, start=start, frm=frm, to=to,
            people=club["people"][0], confirmed=has_time, sid=SID, tip=tip[0], i18n=tr(tip=tip, people=club["people"]),
        ))
    return events


def scrape() -> list[Event]:
    out, errors = [], []
    for c in CLUBS:
        try:
            out.extend(_scrape_club(c))
        except Exception as e:  # noqa: BLE001
            errors.append(f"{c['slug']}: {e}")
    if errors and not out:
        raise RuntimeError("; ".join(errors))
    return out
