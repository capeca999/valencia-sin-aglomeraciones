"""Geoportal del Ajuntament de València (datos abiertos oficiales, capa Tráfico).

- 209 «Ocupación vía pública»: ocupaciones de calle con fechas, horas y ubicación
  (obras, mudanzas… y también actos, rodajes, carreras o manifestaciones).
- 233 «Festejos»: calles ocupadas por fiestas (Fallas, Navidad, fiestas de barrio).
Solo se quedan las que parecen actos con público y duran como mucho una semana.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from ..common import DEBUG, DEBUG_DIR, TZ, Event, clean, fetch, norm, today, tr
from ..geo import find_zones
from .ayto_movilidad import EXCLUDE, KINDS

SID = "geoportal"
NAME = "Ajuntament de València · Geoportal (ocupación de vía pública)"
BASE = "https://geoportal.valencia.es/server/rest/services/OPENDATA/Trafico/MapServer/{}/query"
VIEW = "https://geoportal.valencia.es/apps/GeoportalHome/es/inicio/geodatos-abiertos"
SKIP_TYPES = {"obras", "mudanzas", "mudances", "obres", "contenedor", "contenedores", "andamio", "grua"}


def _query(layer: int) -> dict:
    url = BASE.format(layer) + "?where=1%3D1&outFields=*&outSR=4326&f=json&returnGeometry=true&resultRecordCount=2000"
    return json.loads(fetch(url, timeout=60, tries=5))


def _center(geom: dict | None):
    if not geom:
        return None
    pts = []
    if "x" in geom:
        pts = [[geom["x"], geom["y"]]]
    for key in ("paths", "rings"):
        for part in geom.get(key, []):
            pts.extend(part)
    if not pts:
        return None
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return [round(sum(ys) / len(ys), 5), round(sum(xs) / len(xs), 5)]


def _dt(ms):
    if not ms:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).astimezone(TZ)


def _classify(text: str):
    t = norm(text)
    for kws, typ, lvl, dur in KINDS:
        if any(re.search(r"\b" + re.escape(k), t) for k in kws):
            return typ, lvl
    return None


def scrape() -> list[Event]:
    groups: dict[str, dict] = defaultdict(lambda: {"pts": [], "streets": set()})
    types = Counter()
    for layer in (209, 233):
        data = _query(layer)
        if "error" in data:
            raise RuntimeError(f"capa {layer}: {data['error']}")
        for f in data.get("features", []):
            a = f.get("attributes", {})
            tipo = clean(a.get("tipo_incidencia") or ("FESTEJOS" if layer == 233 else ""))
            desc = clean(a.get("desc_incidencia") or a.get("ocupacion") or "")
            types[tipo] += 1
            ini = _dt(a.get("fecha_inicio") or a.get("fecha_inicio_periodo"))
            fin = _dt(a.get("fecha_fin") or a.get("fecha_fin_periodo"))
            if not ini or not fin:
                continue
            key = f"{layer}-{a.get('id_incidencia') or a.get('objectid')}"
            g = groups[key]
            g.update(layer=layer, tipo=tipo, desc=desc, ini=ini, fin=fin, afect=clean(a.get("tipo_afectacion") or ""))
            if a.get("desc_calle"):
                g["streets"].add(clean(a["desc_calle"]))
            c = _center(f.get("geometry"))
            if c:
                g["pts"].append(c)

    if DEBUG:
        DEBUG_DIR.mkdir(exist_ok=True)
        (DEBUG_DIR / "geoportal_tipos.json").write_text(json.dumps(types.most_common(), ensure_ascii=False, indent=1), encoding="utf-8")

    t0 = today()
    events = []
    for key, g in groups.items():
        if "ini" not in g:
            continue
        text = f"{g['tipo']} {g['desc']} {g['afect']}"
        nt = norm(text)
        if norm(g["tipo"]) in SKIP_TYPES or any(x in nt for x in EXCLUDE):
            continue
        kind = _classify(text) if g["layer"] == 209 else ("Fiesta / desfile", 2)
        if not kind:
            continue
        if g["fin"] - g["ini"] > timedelta(days=7):
            continue  # ocupaciones largas: no son aglomeraciones puntuales
        typ, lvl = kind
        streets = sorted(g["streets"])
        zones = find_zones(" ".join(streets) + " " + g["desc"])
        pts = g["pts"][:30]
        title = g["desc"].capitalize() if g["desc"] else typ
        if streets:
            title += " · " + ", ".join(s.title() for s in streets[:3]) + ("…" if len(streets) > 3 else "")
        day = max(g["ini"].date(), t0)
        while day <= g["fin"].date() and day <= t0 + timedelta(days=60):
            same_start = day == g["ini"].date()
            same_end = day == g["fin"].date()
            frm = g["ini"].strftime("%H:%M") if same_start else "00:00"
            to = g["fin"].strftime("%H:%M") if same_end else "23:59"
            if frm == "00:00" and to in ("23:59", "00:00"):
                frm = to = ""
            ev = Event(
                date=day.isoformat(), title=title[:140], type=typ, zones=zones, level=lvl,
                source_name=NAME, source_url=VIEW, start=frm, frm=frm, to=to, sid=SID,
                tip="Ocupación oficial de la vía pública registrada por el Ayuntamiento." + (" Calles: " + ", ".join(s.title() for s in streets[:6]) + "." if streets else ""),
                raw=f"{g['tipo']} · {g['desc']} · {g['afect']}".strip(" ·"),
                i18n=tr(tip=("", "Ocupació oficial de la via pública registrada per l'Ajuntament." + (" Carrers: " + ", ".join(s.title() for s in streets[:6]) + "." if streets else ""),
                             "Official public-road occupation registered by the City Council." + (" Streets: " + ", ".join(s.title() for s in streets[:6]) + "." if streets else ""))),
            )
            ev.geo = pts  # type: ignore[attr-defined]
            events.append(ev)
            day += timedelta(days=1)
    return events
