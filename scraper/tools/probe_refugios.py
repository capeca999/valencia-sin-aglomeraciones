"""Diagnóstico temporal: lista de refugios climáticos (solo texto y enlaces, sin scripts)."""
import json, pathlib, re
from bs4 import BeautifulSoup
from ..common import _session, BROWSER
OUT = pathlib.Path("probe"); OUT.mkdir(exist_ok=True)
log = []
def get(u):
    try:
        r = _session.get(u, timeout=40, headers=BROWSER); log.append(f"{r.status_code} {u} {len(r.content)}"); return r
    except Exception as e:
        log.append(f"ERR {u} {e}"); return None
for u in ["https://valenciasostenible.com/es/portfolio/refugios-climaticos/", "https://valenciasostenible.com/portfolio/refugios-climaticos/"]:
    r = get(u)
    if r is not None and r.ok:
        s = BeautifulSoup(r.text, "lxml")
        for t in s(["script", "style", "noscript"]): t.decompose()
        links = sorted({a.get("href", "") for a in s.find_all("a")} | {i.get("src", "") for i in s.find_all("iframe")})
        links = [l for l in links if l and not re.search(r"key=|token=|AIza", l)]
        (OUT / "refugios.txt").write_text(s.get_text("\n", strip=True)[:60000] + "\n\n=== LINKS ===\n" + "\n".join(links), encoding="utf-8")
        break
r = get("https://opendata.vlci.valencia.es/api/3/action/package_search?q=refugi&rows=10")
if r is not None and r.ok:
    d = r.json()["result"]["results"]
    (OUT / "ckan.txt").write_text("\n".join(f"{p['name']} | {p['title']} | " + " ; ".join(f"{x.get('format')} {x.get('url')}" for x in p.get("resources", [])) for p in d), encoding="utf-8")
r = get("https://geoportal.valencia.es/server/rest/services/OPENDATA?f=json")
if r is not None and r.ok:
    (OUT / "geoportal_services.txt").write_text(json.dumps(r.json())[:20000], encoding="utf-8")
(OUT / "log.txt").write_text("\n".join(log), encoding="utf-8")
print("\n".join(log))
