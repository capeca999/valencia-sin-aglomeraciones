"""Red de Refugios Climáticos de València (València Sostenible, Ayuntamiento).

Son bibliotecas, museos y centros culturales municipales: espacios climatizados, con
asientos y agua, y normalmente tranquilos. Aquí solo se guardan los que sirven como
«sitio en calma» (se descartan oficinas, juntas municipales, centros de mayores…).
La lista y las coordenadas salen del mapa oficial (Google My Maps) de la red.
"""
from __future__ import annotations

import html
import re

from .common import fetch, norm

PAGE = "https://valenciasostenible.com/es/portfolio/refugios-climaticos/"
KML = "https://www.google.com/maps/d/kml?mid=1694N07k6WSWSUxy-jiJ83iIaRGuiHyo&forcekml=1"
KEEP = [("biblioteca", "biblioteca"), ("museu", "museo"), ("museo", "museo"), ("ivam", "museo"), ("art modern", "museo"),
        ("centre del carme", "museo"), ("cccc", "museo"), ("centro cultural", "cultura"), ("centre cultural", "cultura"),
        ("las naves", "cultura"), ("les naus", "cultura"), ("aben al abbar", "cultura"), ("paleontolog", "museo")]
SKIP = ("museo de las ciencias", "museu de les ciencies", "principe felipe")  # mucho turismo


def kind_of(name: str) -> str | None:
    n = norm(name)
    if any(s in n for s in SKIP):
        return None
    return next((k for key, k in KEEP if key in n), None)


def parse(kml: str) -> list[dict]:
    out, seen = [], set()
    for pm in re.findall(r"<Placemark>(.*?)</Placemark>", kml, re.S):
        nm = re.search(r"<name>(.*?)</name>", pm, re.S)
        co = re.search(r"<coordinates>\s*([-\d.]+),([-\d.]+)", pm)
        if not nm or not co:
            continue
        name = html.unescape(re.sub(r"<!\[CDATA\[|\]\]>", "", nm.group(1))).strip()
        if name.isupper():
            name = name.title().replace(" I ", " i ").replace(" De ", " de ")
        kind = kind_of(name)
        lon, lat = float(co.group(1)), float(co.group(2))
        if not kind or not (39.2 < lat < 39.7 and -0.6 < lon < -0.2) or norm(name) in seen:
            continue
        seen.add(norm(name))
        out.append({"name": name, "kind": kind, "lat": round(lat, 5), "lon": round(lon, 5)})
    return sorted(out, key=lambda r: (r["kind"], r["name"]))


def scrape() -> list[dict]:
    res = parse(fetch(KML, name="refugios_kml", timeout=60))
    if len(res) < 5:
        raise RuntimeError(f"Solo {len(res)} refugios en el mapa oficial (¿ha cambiado?)")
    return res
