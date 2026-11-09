"""Añade, cambia o borra un evento de docs/data/manual.json a partir del formulario de GitHub.

Lo ejecuta .github/workflows/evento-manual.yml cuando el dueño del repositorio rellena el
formulario «Añadir un evento» (o lo edita, o comenta «borrar»).

  python -m scraper.add_manual guardar  (ISSUE_NUMBER, ISSUE_BODY en el entorno)
  python -m scraper.add_manual borrar   (ISSUE_NUMBER)
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import date, timedelta

from .common import ROOT, hm, norm, shift, today
from .geo import ZONES

MANUAL = ROOT / "docs" / "data" / "manual.json"
LEVELS = {"algo de gente": 1, "mucha gente": 2, "muchisima gente": 3}
EMPTY = {"", "_no response_", "none"}


def fields(body: str) -> dict[str, str]:
    """El formulario llega como «### Etiqueta\\n\\nvalor». Devuelve {etiqueta normalizada: valor}."""
    out = {}
    for block in re.split(r"^###\s+", body or "", flags=re.M)[1:]:
        label, _, value = block.partition("\n")
        value = value.strip()
        out[norm(label.strip())] = "" if norm(value) in EMPTY else value
    return out


def get(f: dict, start: str) -> str:
    return next((v for k, v in f.items() if k.startswith(start)), "")


def parse_date(s: str, ref: date | None = None) -> date:
    ref = ref or today()
    s = s.strip()
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})$", s)
    if m:
        return date(int(m[1]), int(m[2]), int(m[3]))
    m = re.match(r"(\d{1,2})[/.\-](\d{1,2})(?:[/.\-](\d{2,4}))?$", s)
    if not m:
        raise ValueError(f"No entiendo la fecha «{s}». Escríbela como 21/11/2026.")
    y = int(m[3]) if m[3] else ref.year
    if y < 100:
        y += 2000
    d = date(y, int(m[2]), int(m[1]))
    if not m[3] and d < ref - timedelta(days=1):
        d = date(y + 1, d.month, d.day)
    return d


def build(f: dict, issue: int) -> list[dict]:
    d1 = parse_date(get(f, "dia"))
    d2 = parse_date(get(f, "ultimo dia")) if get(f, "ultimo dia") else d1
    if d2 < d1 or (d2 - d1).days > 31:
        raise ValueError("El último día tiene que ser después del primero (y como mucho un mes).")
    title = get(f, "nombre").strip()
    if not title:
        raise ValueError("Falta el nombre del evento.")
    names = {norm(z["name"]): k for k, z in ZONES.items()}
    zones, city = [], False
    for z in re.split(r",\s*(?=[A-ZÁÉÍÓÚÀÈÒ])", get(f, "zona")):
        nz = norm(z.strip())
        if nz == "toda la ciudad":
            city = True
        elif nz in names:
            zones.append(names[nz])
    if not zones and not city:
        raise ValueError("Elige al menos una zona.")
    frm, to = hm(get(f, "hora desde")), hm(get(f, "hora hasta"))
    if not frm:
        frm, to = "00:00", "23:59"
    elif not to:
        to = shift(frm, 180)
    extra = norm(get(f, "otros"))
    tags = []
    if "[x] hay petardos" in extra:
        tags.append("fuego")
    if city:
        tags.append("ciudad")
        zones = []
    url = get(f, "enlace")
    ev = []
    d = d1
    while d <= d2:
        ev.append({
            "date": d.isoformat(), "title": title, "type": get(f, "tipo") or "Evento", "zones": zones,
            "level": LEVELS.get(norm(get(f, "cuanta gente")), 2), "start": frm if frm != "00:00" else "",
            "from": frm, "to": to, "people": get(f, "cuantas personas"), "tip": get(f, "consejo"),
            "official": "[x] esta confirmado" in extra, "confirmed": True, "tags": tags,
            "source": {"name": "Añadido a mano", "url": url if url.startswith("http") else ""},
            "issue": issue,
        })
        d += timedelta(days=1)
    return ev


def load() -> dict:
    try:
        return json.loads(MANUAL.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {"events": []}


def save(data: dict) -> None:
    keep_from = (today() - timedelta(days=2)).isoformat()  # los pasados se limpian
    data["events"] = sorted((e for e in data["events"] if e["date"] >= keep_from), key=lambda e: (e["date"], e.get("from", "")))
    MANUAL.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def reply(text: str) -> None:
    p = os.environ.get("REPLY_FILE")
    if p:
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
    print(text)


def main() -> None:
    action = sys.argv[1] if len(sys.argv) > 1 else "guardar"
    issue = int(os.environ["ISSUE_NUMBER"])
    data = load()
    before = len(data["events"])
    data["events"] = [e for e in data["events"] if e.get("issue") != issue]
    if action == "borrar":
        save(data)
        reply("🗑️ Evento quitado de la web. En unos minutos deja de aparecer." if before != len(data["events"]) else "No había ningún evento guardado de este formulario.")
        return
    try:
        evs = build(fields(os.environ.get("ISSUE_BODY", "")), issue)
    except Exception as e:  # noqa: BLE001
        reply(f"⚠️ No lo he podido añadir: {e}\n\nEdita el formulario (lápiz ✏️) para corregirlo.")
        sys.exit(0)
    data["events"].extend(evs)
    save(data)
    e = evs[0]
    days = e["date"] if len(evs) == 1 else f"{evs[0]['date']} → {evs[-1]['date']}"
    zones = ", ".join(ZONES[z]["name"] for z in e["zones"]) or "toda la ciudad"
    hours = "todo el día" if e["from"] == "00:00" else f"{e['from']}–{e['to']}"
    reply(f"✅ Añadido: **{e['title']}** · {days} · {hours} · {zones}.\n\nEn unos minutos sale en la web, en los calendarios y en los avisos del móvil. "
          "Para cambiarlo, edita el formulario (lápiz ✏️); para quitarlo, comenta `borrar`.")


if __name__ == "__main__":
    main()
