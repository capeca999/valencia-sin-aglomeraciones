"""Descarga los pictogramas ARASAAC que usa la web a docs/pictos/.

Pictogramas: Sergio Palao. Origen: ARASAAC (https://arasaac.org). Licencia: CC BY-NC-SA.
Propiedad: Gobierno de Aragón (España).

Para cambiar un pictograma, pon su número en FIXED (se ve en arasaac.org) y vuelve a ejecutar.
"""
from __future__ import annotations

import json
from urllib.parse import quote

import requests

from .common import DEBUG, DEBUG_DIR, HEADERS, ROOT

OUT = ROOT / "docs" / "pictos"
# clave -> palabra a buscar en ARASAAC (español)
WANTED = {
    "futbol": "fútbol",
    "baloncesto": "baloncesto",
    "concierto": "concierto",
    "manifestacion": "manifestación",
    "huelga": "huelga",
    "fuegos": "fuegos artificiales",
    "petardo": "petardo",
    "carrera": "carrera",
    "desfile": "desfile",
    "fiesta": "fiesta",
    "gente": "multitud",
    "tranquilo": "tranquilo",
    "silencio": "silencio",
    "ruido": "ruido",
    "biblioteca": "biblioteca",
    "parque": "parque",
    "jardin": "jardín",
    "supermercado": "supermercado",
    "museo": "museo",
    "playa": "playa",
    "calle_cortada": "calle cortada",
    "metro": "metro",
}
FIXED: dict[str, int] = {}  # clave -> id de ARASAAC elegido a mano


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    index_path = OUT / "pictos.json"
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        index = {}
    s = requests.Session()
    s.headers.update(HEADERS)
    for key, word in WANTED.items():
        pid = FIXED.get(key) or index.get(key, {}).get("id")
        candidates = []
        if not pid:
            try:
                r = s.get(f"https://api.arasaac.org/v1/pictograms/es/search/{quote(word)}", timeout=30)
                r.raise_for_status()
                res = r.json()
                candidates = [x["_id"] for x in res[:6]]
                pid = candidates[0] if candidates else None
            except Exception as e:  # noqa: BLE001
                print("sin resultado:", key, e)
                continue
        if not pid:
            continue
        png = OUT / f"{key}.png"
        if not png.exists() or index.get(key, {}).get("id") != pid:
            img = s.get(f"https://static.arasaac.org/pictograms/{pid}/{pid}_300.png", timeout=30)
            img.raise_for_status()
            png.write_bytes(img.content)
        if DEBUG:
            alt_dir = DEBUG_DIR / "pictos_alt"
            alt_dir.mkdir(parents=True, exist_ok=True)
            for aid in candidates[1:5]:
                try:
                    a = s.get(f"https://static.arasaac.org/pictograms/{aid}/{aid}_300.png", timeout=30)
                    (alt_dir / f"{key}_{aid}.png").write_bytes(a.content)
                except Exception:  # noqa: BLE001
                    pass
        index[key] = {"id": pid, "word": word, "alt_ids": candidates or index.get(key, {}).get("alt_ids", [])}
        print(key, pid)
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
