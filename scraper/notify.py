"""Avisos al móvil con ntfy (https://ntfy.sh): uno general y uno por barrio.

  python -m scraper.notify morning   -> «Hoy …»     (eventos de hoy)
  python -m scraper.notify evening   -> «🌙 Mañana …» (eventos de mañana)
  añade --dry-run para ver los mensajes sin enviarlos

Canales (temas de ntfy), con BASE = ntfy_topic de config.json:
  BASE            -> toda Valencia
  BASE-<barrio>   -> solo lo que afecta a ese barrio (centro, ruzafa, sur…)
Solo se avisa de eventos con «Mucha gente» o más.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import timedelta

import requests

from .common import ROOT, today
from .geo import AREAS, areas_of

LEVEL = {1: "algo de gente", 2: "mucha gente", 3: "muchísima gente"}


def _line(e: dict, zones: dict) -> str:
    where = ", ".join(zones[z]["name"] for z in e.get("zones", []) if z in zones) or ("toda la ciudad" if e["type"] == "Huelga" else "ver la web")
    when = f"{e['from']}–{e['to']}" if e.get("from") else (f"desde las {e['start']}" if e.get("start") else "hora sin anunciar")
    return f"• {where} · {when}\n  {e['title'][:90]}"


def build(events: list[dict], zones: dict, day: str, evening: bool, place: str | None) -> tuple[str, str, int] | None:
    evs = [e for e in events if e["date"] == day and e["level"] >= 2]
    if not evs:
        return None
    top = max(e["level"] for e in evs)
    tags = {t for e in evs for t in e.get("tags", [])}
    when = "Mañana" if evening else "Hoy"
    if "ciudad" in tags:
        head = f"{when}: toda València llena de gente (Fallas)"
    else:
        head = f"{when}{' en ' + place if place else ''}: {LEVEL[top]}" + ("" if place else f" en {len(evs)} sitio{'s' if len(evs) > 1 else ''}")
    title = ("🌙 " if evening else "") + ("🔥 " if "fuego" in tags else "") + head
    return title, "\n".join(_line(e, zones) for e in evs), top


def messages(data: dict, base: str, evening: bool) -> list[tuple[str, str, str, int]]:
    """Lista de (tema, título, texto, nivel) a enviar."""
    day = (today() + timedelta(days=1 if evening else 0)).isoformat()
    out = []
    m = build(data["events"], data["zones"], day, evening, None)
    if m:
        out.append((base, *m))
    for area, (name, _) in AREAS.items():
        mine = [e for e in data["events"] if area in areas_of(e)]
        m = build(mine, data["zones"], day, evening, name)
        if m:
            out.append((f"{base}-{area}", *m))
    return out


def main() -> None:
    args = sys.argv[1:]
    evening = "evening" in args
    dry = "--dry-run" in args
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    base = os.environ.get("NTFY_TOPIC") or cfg.get("ntfy_topic")
    if not base:
        print("Sin tema de ntfy: no se envía nada")
        return
    data = json.loads((ROOT / "docs" / "data" / "events.json").read_text(encoding="utf-8"))
    msgs = messages(data, base, evening)
    if not msgs:
        print("No hay eventos grandes: no se envía nada")
    for topic, title, body, top in msgs:
        print(f"[{topic}] {title}\n{body}\n")
        if dry:
            continue
        try:
            r = requests.post(f"https://ntfy.sh/{topic}", data=body.encode("utf-8"), timeout=20, headers={
                "Title": title.encode("utf-8"),
                "Priority": "high" if top >= 3 else "default",
                "Tags": "fire" if "🔥" in title else ("crescent_moon" if evening else ("warning" if top >= 3 else "information_source")),
                "Click": cfg.get("site_url", ""),
            })
            r.raise_for_status()
        except Exception as e:  # noqa: BLE001
            print("  error al enviar:", e)
        time.sleep(1)


if __name__ == "__main__":
    main()
