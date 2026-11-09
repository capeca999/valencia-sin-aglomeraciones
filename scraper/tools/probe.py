"""Diagnóstico temporal: descarga páginas candidatas a debug/probe/ para ver su estructura."""
import pathlib, re, sys
from ..common import _session, BROWSER
OUT = pathlib.Path("debug/probe"); OUT.mkdir(parents=True, exist_ok=True)
URLS = {
 "fv_home": "https://www.feriavalencia.com/",
 "fv_cal": "https://www.feriavalencia.com/calendario/",
 "fv_cal2": "https://www.feriavalencia.com/calendario-de-ferias/",
 "fv_wpjson": "https://www.feriavalencia.com/wp-json/",
 "fv_types": "https://www.feriavalencia.com/wp-json/wp/v2/types",
 "ct_nov": "https://www.cruisetimetables.com/valenciaspainschedule-nov2026.html",
 "ct_main": "https://www.cruisetimetables.com/valencia-spain-cruise-ship-schedule.html",
 "gw_nov": "https://gangwaze.com/cruise-port-schedule/valencia-spain/november-2026",
 "meteoalarm": "https://feeds.meteoalarm.org/feeds/meteoalarm-legacy-atom-spain",
 "aemet_rss_idx": "https://www.aemet.es/es/rss_info/avisos/esp",
 "aemet_rss_77": "https://www.aemet.es/documentos_d/eltiempo/prediccion/avisos/rss/CAP_AFAC77_RSS.xml",
 "dogv_ferias": "https://dogv.gva.es/datos/2025/12/10/pdf/2025_46948_es.pdf",
}
for k, u in URLS.items():
    try:
        r = _session.get(u, timeout=30, headers=BROWSER)
        ext = ".pdf" if u.endswith(".pdf") else ".txt"
        (OUT / (k + ext)).write_bytes(r.content[:400000])
        (OUT / (k + ".status")).write_text(f"{r.status_code} {r.url}\n{dict(r.headers)}")
        print(r.status_code, k, len(r.content))
    except Exception as e:
        (OUT / (k + ".err")).write_text(repr(e)); print("ERR", k, e)
