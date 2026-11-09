"""Ruido medido por los sonómetros del Ayuntamiento (barrio de Ruzafa).

Datos abiertos oficiales (opendata.vlci.valencia.es): un conjunto por sensor con datos
diarios en dBA. Se toma el último día disponible de cada sensor:
  LAeq_d = día (7–19 h), LAeq_e = tarde (19–23 h), LAeq_n = noche (23–7 h).
"""
from __future__ import annotations

import csv
import io
import json
import re

from .common import DEBUG, DEBUG_DIR, fetch

SEARCH = "https://opendata.vlci.valencia.es/api/3/action/package_search?q={}&rows=60"
QUERIES = ["soroll Russafa", "sensor de ruido Ruzafa"]
COORD = re.compile(r"(39\.\d{3,})\s*,\s*(-0\.\d{3,})")


def _num(v):
    try:
        return round(float(str(v).replace(",", ".")), 1)
    except (TypeError, ValueError):
        return None


def _col(row: dict, *names):
    low = {k.lower().strip(): k for k in row}
    for n in names:
        if n.lower() in low:
            return row[low[n.lower()]]
    return None


def scrape() -> list[dict]:
    pkgs = {}
    for q in QUERIES:
        data = json.loads(fetch(SEARCH.format(q.replace(" ", "+")), timeout=60))
        for p in data.get("result", {}).get("results", []):
            pkgs[p["name"]] = p
    out = []
    for i, p in enumerate(pkgs.values()):
        text = (p.get("notes") or "") + " " + (p.get("title") or "")
        m = COORD.search(text)
        if not m or "soroll" not in text.lower() and "ruido" not in text.lower():
            continue
        csv_res = next((r for r in p.get("resources", []) if (r.get("format") or "").upper() == "CSV"), None)
        if not csv_res:
            continue
        try:
            raw = fetch(csv_res["url"], timeout=60)
        except Exception:  # noqa: BLE001
            continue
        if DEBUG and i == 0:
            DEBUG_DIR.mkdir(exist_ok=True)
            (DEBUG_DIR / "ruido_muestra.csv").write_text(raw[:3000], encoding="utf-8")
        sample = raw[:2000]
        delim = ";" if sample.count(";") > sample.count(",") else ","
        rows = list(csv.DictReader(io.StringIO(raw), delimiter=delim))
        if not rows:
            continue
        def day(r):
            return str(_col(r, "dateObserved", "DateObserved", "fecha", "recvTime", "RecvTime") or "")
        rows.sort(key=day)
        last = rows[-1]
        place = re.sub(r"^.*?(?:carrer|calle)\s+", "", p.get("title") or "", flags=re.I).strip() or p["name"]
        out.append({
            "id": p["name"],
            "name": place[:80],
            "lat": float(m.group(1)), "lon": float(m.group(2)),
            "date": day(last)[:10],
            "laeq": _num(_col(last, "LAeq")),
            "laeq_d": _num(_col(last, "LAeq_d")),
            "laeq_e": _num(_col(last, "LAeq_e")),
            "laeq_n": _num(_col(last, "LAeq_n")),
            "source": f"https://opendata.vlci.valencia.es/dataset/{p['name']}",
        })
    return out
