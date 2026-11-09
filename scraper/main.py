"""Recoge eventos de fuentes oficiales y genera docs/data/events.json.

Uso:  python -m scraper.main            (VSA_DEBUG=1 guarda el HTML descargado en debug/)
"""
from __future__ import annotations

import json
import os
import traceback
from datetime import date, timedelta

from .common import ROOT, Event, norm, now, today
from .geo import PATTERNS, zones_json
from .sources import ayto_movilidad, ayto_noticias, geoportal, laliga, roig_arena, visitvalencia

OUT = ROOT / "docs" / "data" / "events.json"
MANUAL = ROOT / "docs" / "data" / "manual.json"

# Orden = prioridad cuando dos fuentes describen el mismo evento
SOURCES = [
    ("geoportal", "Ajuntament de València · Geoportal (ocupación de vía pública y festejos)", geoportal.scrape),
    ("laliga", "LaLiga (Valencia CF y Levante UD)", laliga.scrape),
    ("roig_arena", "Roig Arena (web oficial)", roig_arena.scrape),
    ("visitvalencia", "Visit València (calendario Valencia Basket)", visitvalencia.scrape),
]


class _Skip(Exception):
    pass


def _load_previous() -> dict:
    try:
        return json.loads(OUT.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def _same(a: dict, b: dict) -> bool:
    """¿Son el mismo evento? Mismo día, alguna zona en común y misma hora (o sin hora)."""
    if a["date"] != b["date"] or not set(a["zones"]) & set(b["zones"]):
        return False
    generic = ("Evento", "Aviso")
    if a["type"] != b["type"] and a["type"] not in generic and b["type"] not in generic:
        return False
    if a["start"] and b["start"]:
        h1, m1 = map(int, a["start"].split(":"))
        h2, m2 = map(int, b["start"].split(":"))
        diff = abs((h1 * 60 + m1) - (h2 * 60 + m2))
        return diff <= 90
    return a["type"] == b["type"]


def _merge(events: list[dict]) -> list[dict]:
    out: list[dict] = []
    for e in events:
        dup = next((o for o in out if _same(o, e)), None)
        if dup is None:
            out.append(e)
            continue
        # el calendario oficial del club manda sobre la hora de apertura de puertas del recinto
        if e.get("sid") == "visitvalencia" and dup.get("sid") == "roig_arena" and e.get("start"):
            dup["start"], dup["from"], dup["to"] = e["start"], e["from"], e["to"]
        # completar huecos del primero con el segundo y anotar la otra fuente
        for k in ("start", "from", "to", "people"):
            if not dup.get(k) and e.get(k):
                dup[k] = e[k]
        dup["level"] = max(dup["level"], e["level"])
        if dup["type"] in ("Evento", "Aviso") and e["type"] not in ("Evento", "Aviso"):
            dup["type"], dup["title"] = e["type"], e["title"] + " · " + dup["title"]
        extra = dup.setdefault("also", [])
        if e["source"]["url"] != dup["source"]["url"] and e["source"] not in extra:
            extra.append(e["source"])
    return out


def run() -> dict:
    prev = _load_previous()
    t = today()
    events: list[dict] = []
    status = []
    sources = list(SOURCES)
    # valencia.es rechaza las peticiones desde los servidores de GitHub; se intenta solo si se pide (p. ej. en local).
    if os.environ.get("VSA_AYTO_WEB") == "1":
        sources.insert(1, ("ayto_movilidad", "Ajuntament de València · Incidencias y previsiones de tráfico", ayto_movilidad.scrape))
    for sid, label, fn in sources:
        try:
            found: list[Event] = fn()
            events.extend(e.to_json() for e in found)
            status.append({"id": sid, "name": label, "ok": True, "count": len(found)})
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            kept = [x for x in prev.get("events", []) if x.get("sid") == sid and x["date"] >= t.isoformat()]
            events.extend(kept)
            status.append({"id": sid, "name": label, "ok": False, "count": len(kept), "error": str(e)[:300]})

    try:
        if os.environ.get("VSA_AYTO_WEB") != "1":
            raise _Skip()
        notices = ayto_noticias.scrape()
        status.append({"id": "ayto_noticias", "name": "Ajuntament de València · Noticias de movilidad", "ok": True, "count": len(notices)})
    except _Skip:
        notices = []
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        notices = prev.get("notices", [])
        status.append({"id": "ayto_noticias", "name": "Ajuntament de València · Noticias de movilidad", "ok": False, "count": len(notices), "error": str(e)[:300]})

    # Eventos añadidos a mano (docs/data/manual.json)
    try:
        manual = json.loads(MANUAL.read_text(encoding="utf-8")).get("events", [])
    except Exception:  # noqa: BLE001
        manual = []
    for m in manual:
        m.setdefault("official", False)
        m.setdefault("sid", "manual")
        m.setdefault("zones", [])
        m.setdefault("start", "")
        m.setdefault("tags", [])
        events.append(m)

    lo, hi = (t - timedelta(days=1)).isoformat(), (t + timedelta(days=60)).isoformat()
    events = [e for e in events if lo <= e["date"] <= hi]
    events.sort(key=lambda e: (e["date"], e.get("start") or "99", -e["level"]))
    events = _merge(events)

    data = {
        "updated": now().isoformat(timespec="minutes"),
        "zones": zones_json(),
        "patterns": PATTERNS,
        "events": events,
        "notices": notices,
        "sources": status,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(events)} eventos, {len(notices)} avisos")
    for s in status:
        print(("OK  " if s["ok"] else "FALLO ") + f"{s['id']}: {s['count']}" + (f"  ({s.get('error')})" if not s["ok"] else ""))
    return data


if __name__ == "__main__":
    run()
