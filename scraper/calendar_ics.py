"""Genera calendarios .ics para suscribirse desde Google Calendar, Apple o Outlook.

  docs/cal/valencia.ics      -> toda Valencia
  docs/cal/<barrio>.ics      -> solo lo que afecta a ese barrio (centro, ruzafa, sur…)

Solo incluye eventos con «Mucha gente» o más. Los calendarios suscritos se actualizan
solos (cada pocas horas, según la aplicación).
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta, timezone

from .common import ROOT, TZ
from .geo import AREAS, areas_of

OUT = ROOT / "docs" / "cal"
LEVEL = {1: "Algo de gente", 2: "Mucha gente", 3: "Muchísima gente"}
SITE = "https://capeca999.github.io/valencia-sin-aglomeraciones/"


def _esc(s: str) -> str:
    return (s or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\r", "").replace("\n", "\\n")


def _fold(line: str) -> str:
    """Las líneas de un .ics no pueden pasar de 75 octetos: se parten con CRLF + espacio."""
    out, cur = [], b""
    for ch in line:
        b = ch.encode("utf-8")
        if len(cur) + len(b) > 74:
            out.append(cur.decode("utf-8"))
            cur = b" " + b
        else:
            cur += b
    out.append(cur.decode("utf-8"))
    return "\r\n".join(out)


def _utc(d: date, hm: str) -> datetime:
    h, m = map(int, hm.split(":"))
    return datetime(d.year, d.month, d.day, h % 24, m, tzinfo=TZ).astimezone(timezone.utc)


def _vevent(e: dict, zones: dict, stamp: str) -> list[str]:
    d = date.fromisoformat(e["date"])
    uid = hashlib.sha1(f"{e['date']}|{e.get('sid')}|{e['title']}".encode()).hexdigest()[:20] + "@valenciasinaglomeraciones"
    where = ", ".join(zones[z]["name"] for z in e.get("zones", []) if z in zones) or ("Toda la ciudad" if e.get("type") == "Huelga" else "València")
    fire = "🔥 " if "fuego" in (e.get("tags") or []) else ""
    lines = ["BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{stamp}"]
    frm, to = e.get("from") or "", e.get("to") or ""
    if frm and to and not (frm == "00:00" and to in ("23:59", "00:00")):
        start = _utc(d, frm)
        end = _utc(d, to)
        if end <= start:  # termina pasada la medianoche
            end += timedelta(days=1)
        lines += [f"DTSTART:{start:%Y%m%dT%H%M%SZ}", f"DTEND:{end:%Y%m%dT%H%M%SZ}"]
    else:
        lines += [f"DTSTART;VALUE=DATE:{d:%Y%m%d}", f"DTEND;VALUE=DATE:{d + timedelta(days=1):%Y%m%d}"]
    desc = f"{LEVEL.get(e['level'], '')}. Zona a evitar: {where}.\n{e.get('tip', '')}\n\nFuente: {e['source']['name']} {e['source'].get('url', '')}\n{SITE}"
    lines += [
        f"SUMMARY:{_esc(fire + LEVEL.get(e['level'], '') + ': ' + e['title'])}",
        f"LOCATION:{_esc(where)}",
        f"DESCRIPTION:{_esc(desc)}",
        f"URL:{SITE}",
        "TRANSP:TRANSPARENT",  # no marca la agenda como ocupada
        "END:VEVENT",
    ]
    return lines


def _calendar(name: str, events: list[dict], zones: dict) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Valencia sin aglomeraciones//ES", "CALSCALE:GREGORIAN",
             "METHOD:PUBLISH", f"X-WR-CALNAME:{_esc(name)}", "X-WR-TIMEZONE:Europe/Madrid",
             "X-WR-CALDESC:" + _esc("Dónde y cuándo habrá mucha gente en València. " + SITE),
             "REFRESH-INTERVAL;VALUE=DURATION:PT6H", "X-PUBLISHED-TTL:PT6H"]
    for e in events:
        lines += _vevent(e, zones, stamp)
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(x) for x in lines) + "\r\n"


def build(data: dict) -> dict[str, int]:
    OUT.mkdir(parents=True, exist_ok=True)
    big = [e for e in data["events"] if e["level"] >= 2]
    counts = {}
    (OUT / "valencia.ics").write_text(_calendar("València sin aglomeraciones", big, data["zones"]), encoding="utf-8", newline="")
    counts["valencia"] = len(big)
    for area, (aname, _) in AREAS.items():
        evs = [e for e in big if area in areas_of(e)]
        (OUT / f"{area}.ics").write_text(_calendar(f"Sin aglomeraciones · {aname}", evs, data["zones"]), encoding="utf-8", newline="")
        counts[area] = len(evs)
    return counts


if __name__ == "__main__":
    print(build(json.loads((ROOT / "docs" / "data" / "events.json").read_text(encoding="utf-8"))))
