"""Datos del Geoportal del Ayuntamiento que se pintan en el mapa:

- Fallas: ubicación de cada monumento fallero (con su sección: las de Sección Especial
  atraen a muchísima gente) y las «zonas de actividades», es decir, las calles que ocupa
  cada falla con carpas, escenarios y verbenas. Se guarda aparte (docs/data/fallas.json)
  porque solo se carga en el mapa los días grandes de Fallas.
- ZAS: zonas acústicamente saturadas (declaradas por el Ayuntamiento por el ruido del ocio
  nocturno).
"""
from __future__ import annotations

import json
from datetime import datetime

from .common import ROOT, TZ, clean, fetch

BASE = "https://geoportal.valencia.es/server/rest/services/OPENDATA"
Q = "/query?where=1%3D1&outFields=*&outSR=4326&f=geojson&resultRecordCount=2000"
MONUMENTS = BASE + "/Turismo/MapServer/215" + Q
ACTIVITY = BASE + "/Turismo/MapServer/206" + Q
ZAS = BASE + "/SociedadBienestar/MapServer/5" + Q
OUT = ROOT / "docs" / "data" / "fallas.json"


def _get(url: str) -> list[dict]:
    d = json.loads(fetch(url, timeout=90, tries=5))
    if "features" not in d:
        raise RuntimeError(f"Respuesta inesperada del Geoportal: {str(d)[:200]}")
    return d["features"]


def _rings(geom: dict | None) -> list[list[list[float]]]:
    """Polígonos GeoJSON -> lista de anillos [[lat, lon], …] (Leaflet usa lat, lon)."""
    if not geom:
        return []
    polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"] if geom["type"] == "MultiPolygon" else []
    out = []
    for poly in polys:
        for ring in poly[:1]:  # solo el contorno exterior
            pts = [[round(y, 5), round(x, 5)] for x, y in ring]
            if len(pts) >= 3:
                out.append(pts)
    return out


def _title(s: str | None) -> str:
    s = clean(s or "")
    return s.title().replace(" I ", " i ").replace(" De ", " de ").replace(" Del ", " del ").replace(" La ", " la ") if s.isupper() else s


def build_fallas() -> int:
    mons, names = [], {}
    for f in _get(MONUMENTS):
        p, g = f.get("properties") or {}, f.get("geometry")
        name = _title(p.get("nombre"))
        if not name or not g or g.get("type") != "Point":
            continue
        lon, lat = g["coordinates"][:2]
        sec = clean(str(p.get("seccion") or ""))
        names[p.get("id_falla")] = name
        mons.append({"id": p.get("id_falla"), "name": name, "sec": sec, "lema": clean(p.get("lema") or ""),
                     "lat": round(lat, 5), "lon": round(lon, 5)})
    zones = []
    for f in _get(ACTIVITY):
        p = f.get("properties") or {}
        rings = _rings(f.get("geometry"))
        if rings:
            zones.append({"falla": p.get("id_falla"), "name": names.get(p.get("id_falla"), ""), "rings": rings})
    if len(mons) < 50:
        raise RuntimeError(f"Solo {len(mons)} fallas en el Geoportal (¿ha cambiado?)")
    OUT.write_text(json.dumps({"updated": datetime.now(TZ).isoformat(timespec="minutes"), "monuments": mons, "zones": zones},
                              ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return len(mons)


def scrape_zas() -> list[dict]:
    out = []
    for f in _get(ZAS):
        p = f.get("properties") or {}
        name = next((clean(str(v)) for k, v in p.items() if isinstance(v, str) and any(t in k.lower() for t in ("nom", "zona", "denom", "desc"))), "")
        rings = _rings(f.get("geometry"))
        if rings:
            out.append({"name": _title(name), "rings": rings, "props": {k: v for k, v in p.items() if isinstance(v, (str, int)) and k.lower() not in ("objectid", "shape")}})
    if not out:
        raise RuntimeError("No hay zonas ZAS en el Geoportal")
    return out
