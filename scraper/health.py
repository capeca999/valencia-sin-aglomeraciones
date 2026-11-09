"""Aviso privado al responsable de la web cuando algo deja de funcionar.

Se ejecuta cada mañana después de actualizar los datos. Avisa (por el tema de ntfy
«admin_topic» de config.json) si una fuente:
  - lleva 2 días o más fallando (no responde o da error), o
  - lleva 2 días o más devolviendo 0 resultados cuando normalmente devuelve datos
    (suele significar que la web de origen ha cambiado su diseño).

  python -m scraper.health            -> revisa y avisa si hace falta
  python -m scraper.health --failed   -> avisa de que la actualización diaria ha fallado entera
  añade --dry-run para no enviar nada
"""
from __future__ import annotations

import json
import sys

import requests

from .common import ROOT

# Fuentes que casi siempre tienen datos: si dan 0 varios días seguidos, algo pasa
EXPECT_DATA = {"laliga", "roig_arena", "visitvalencia", "fiestas", "ruido"}
DAYS = 2


def problems(data: dict) -> list[str]:
    out = []
    names = {s["id"]: s["name"] for s in data.get("sources", [])}
    for sid, h in (data.get("health") or {}).items():
        name = names.get(sid, sid)
        if h.get("fail_days", 0) >= DAYS:
            out.append(f"• {name}: lleva {h['fail_days']} días sin responder. Último error: {h.get('last_error', '')[:160]}")
        elif sid in EXPECT_DATA and h.get("zero_days", 0) >= DAYS:
            out.append(f"• {name}: lleva {h['zero_days']} días sin encontrar ningún evento. Puede que su web haya cambiado.")
    return out


def send(topic: str, title: str, body: str, dry: bool) -> None:
    print(f"[{topic}] {title}\n{body}")
    if dry:
        return
    r = requests.post(f"https://ntfy.sh/{topic}", data=body.encode("utf-8"), timeout=20,
                      headers={"Title": title.encode("utf-8"), "Priority": "high", "Tags": "rotating_light"})
    r.raise_for_status()


def main() -> None:
    dry = "--dry-run" in sys.argv
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    topic = cfg.get("admin_topic")
    if not topic:
        print("Sin admin_topic en config.json")
        return
    repo = "https://github.com/capeca999/valencia-sin-aglomeraciones/actions"
    if "--failed" in sys.argv:
        send(topic, "⚠️ La actualización de hoy ha fallado",
             f"La web no se ha podido actualizar. Sigue mostrando los datos anteriores.\nDetalles: {repo}", dry)
        return
    data = json.loads((ROOT / "docs" / "data" / "events.json").read_text(encoding="utf-8"))
    p = problems(data)
    if not p:
        print("Todo funciona")
        return
    send(topic, f"⚠️ {len(p)} fuente{'s' if len(p) > 1 else ''} con problemas",
         "\n".join(p) + f"\n\nLa web sigue funcionando con los datos anteriores de esas fuentes.\nDetalles: {repo}", dry)


if __name__ == "__main__":
    main()
