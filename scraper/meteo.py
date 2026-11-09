"""Avisos meteorológicos de AEMET para València (vía MeteoAlarm, el agregador oficial europeo).

València ciudad está en la zona de aviso «Litoral norte de Valencia». Solo se guardan los
avisos vigentes o próximos de esa zona. No son aglomeraciones, pero importan: tormentas
(ruido de truenos), calor extremo, lluvias fuertes o viento.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from .common import TZ, fetch

URL = "https://feeds.meteoalarm.org/feeds/meteoalarm-legacy-atom-spain"
AREA = "litoral norte de valencia"
LEVEL = {"Moderate": 1, "Severe": 2, "Extreme": 3}  # amarillo, naranja, rojo
KINDS = ["thunderstorm", "rain", "wind", "high-temperature", "low-temperature", "snow", "coastal", "fog", "forest-fire", "flood"]


def _kind(ev: str) -> str:
    e = ev.lower().replace(" ", "-")
    return next((k for k in KINDS if k in e), "other")


def _tag(entry: str, name: str) -> str:
    m = re.search(rf"<cap:{name}>([^<]*)</cap:{name}>", entry)
    return m.group(1).strip() if m else ""


def parse(xml: str, now: datetime | None = None) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    out, seen = [], set()
    for entry in xml.split("<entry>")[1:]:
        if AREA not in _tag(entry, "areaDesc").lower():
            continue
        sev = LEVEL.get(_tag(entry, "severity"))
        if not sev or _tag(entry, "message_type") == "Cancel":
            continue
        try:
            onset = datetime.fromisoformat(_tag(entry, "onset") or _tag(entry, "effective"))
            expires = datetime.fromisoformat(_tag(entry, "expires"))
        except ValueError:
            continue
        if expires < now:
            continue
        kind = _kind(_tag(entry, "event"))
        a, b = onset.astimezone(TZ), expires.astimezone(TZ)
        key = (kind, a.isoformat(), b.isoformat())
        if key in seen:
            continue
        seen.add(key)
        out.append({"kind": kind, "level": sev, "from": a.isoformat(timespec="minutes"), "to": b.isoformat(timespec="minutes"),
                    "url": "https://www.aemet.es/es/eltiempo/prediccion/avisos?k=val"})
    # si hay varios avisos del mismo tipo, uno por tipo y día con el nivel más alto
    out.sort(key=lambda w: (w["from"], -w["level"]))
    return out


def days_of(w: dict) -> list[str]:
    a, b = datetime.fromisoformat(w["from"]).date(), (datetime.fromisoformat(w["to"]) - timedelta(minutes=1)).date()
    return [(a + timedelta(days=i)).isoformat() for i in range((b - a).days + 1)]


def scrape() -> list[dict]:
    return parse(fetch(URL, name="meteoalarm"))
