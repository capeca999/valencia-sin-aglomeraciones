"""Envía el aviso del día al móvil con ntfy (https://ntfy.sh).

Solo avisa si hoy hay algo con «Mucha gente» o más. Para recibirlo, instala la app ntfy
y suscríbete al tema que aparece en config.json.
"""
from __future__ import annotations

import json
import os

import requests

from .common import ROOT, today

LEVEL = {1: "Algo de gente", 2: "Mucha gente", 3: "Muchísima gente"}


def build(data: dict, day: str) -> tuple[str, str, int] | None:
    evs = [e for e in data["events"] if e["date"] == day and e["level"] >= 2]
    if not evs:
        return None
    zones = data["zones"]
    lines = []
    for e in evs:
        where = ", ".join(zones[z]["name"] for z in e["zones"] if z in zones) or ("toda la ciudad" if e["type"] == "Huelga" else "ver detalles en la web")
        when = f"{e['from']}–{e['to']}" if e.get("from") else (f"desde las {e['start']}" if e.get("start") else "hora sin anunciar")
        lines.append(f"• {where} · {when}\n  {e['title'][:90]}")
    top = max(e["level"] for e in evs)
    tags = {t for e in evs for t in e.get("tags", [])}
    if "ciudad" in tags:
        title = "🔥 Hoy: toda València llena de gente (Fallas)"
    else:
        title = ("🔥 " if "fuego" in tags else "") + f"Hoy: {LEVEL[top].lower()} en {len(evs)} sitio{'s' if len(evs) > 1 else ''}"
    return title, "\n".join(lines), top


def main() -> None:
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    topic = os.environ.get("NTFY_TOPIC") or cfg.get("ntfy_topic")
    if not topic:
        print("Sin tema de ntfy: no se envía aviso")
        return
    data = json.loads((ROOT / "docs" / "data" / "events.json").read_text(encoding="utf-8"))
    msg = build(data, today().isoformat())
    if not msg:
        print("Hoy no hay eventos grandes: no se envía aviso")
        return
    title, body, top = msg
    r = requests.post(
        f"https://ntfy.sh/{topic}",
        data=body.encode("utf-8"),
        headers={
            "Title": title.encode("utf-8"),
            "Priority": "high" if top >= 3 else "default",
            "Tags": "fire" if "🔥" in title else ("warning" if top >= 3 else "information_source"),
            "Click": cfg.get("site_url", ""),
        },
        timeout=20,
    )
    r.raise_for_status()
    print("Aviso enviado:", title)


if __name__ == "__main__":
    main()
