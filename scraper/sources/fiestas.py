"""Calendario de fiestas con fecha fija en València (se repiten cada año).

No depende de ninguna web: son tradiciones con fechas conocidas. Las horas son las
habituales y pueden variar un poco cada año; el aviso enlaza al programa oficial.
"""
from __future__ import annotations

from datetime import date, timedelta

from ..common import Event, today

SID = "fiestas"
NAME = "Calendario de fiestas de València (fechas fijas)"
FALLAS_URL = "https://www.visitvalencia.com/agenda-valencia/fallas-valencia"
RUIDO = " Hay petardos, mucho ruido y olor a pólvora en toda la ciudad; si te afecta el ruido, lleva protección auditiva."
BARRIOS = ["ayuntamiento", "san_agustin", "colon", "reina", "mercado", "carmen", "ruzafa", "parterre", "america"]


def _last_sunday(year: int, month: int) -> date:
    d = date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)
    return d - timedelta(days=(d.weekday() - 6) % 7)


def _ev(d, title, typ, zones, level, frm, to, tip, people="decenas de miles de personas", url=FALLAS_URL, start=None, tags=None):
    return Event(date=d.isoformat(), title=title, type=typ, zones=zones, level=level, source_name=NAME, source_url=url,
                 start=start or frm, frm=frm, to=to, people=people, tip=tip, official=False, confirmed=True,
                 approx=True, sid=SID, tags=tags or ["fuego"])


def _year(y: int) -> list[Event]:
    ev = []
    # Fallas
    ev.append(_ev(_last_sunday(y, 2), "Fallas: la Crida (inicio de las Fallas)", "Fiesta / desfile", ["carmen"], 3, "18:30", "21:30",
                  "La Crida se celebra en las Torres de Serranos, con fuegos artificiales al final." + RUIDO))
    for day in range(1, 20):
        d = date(y, 3, day)
        lvl = 3 if day >= 10 else 2
        ev.append(_ev(d, "Fallas: mascletà en la Plaza del Ayuntamiento", "Fiesta / desfile", ["ayuntamiento", "san_agustin", "colon"], lvl,
                      "12:45", "14:45", "La mascletà es a las 14:00 y es MUY ruidosa (se nota en todo el centro). La plaza se llena desde una hora antes." + RUIDO, start="14:00"))
    for day in (14, 15, 16, 17, 18, 19):
        ev.append(_ev(date(y, 3, day), "Semana de Fallas: TODA la ciudad llena de gente, fuego y petardos", "Fiesta / desfile", BARRIOS, 3,
                      "", "", "Es la semana más difícil del año en València: cientos de miles de personas en la calle, música y petardos en casi todos los barrios de día y de noche, calles cortadas y metro abarrotado. Si puedes, organiza estos días para salir lo justo, o pásalos fuera de la ciudad." + RUIDO,
                      people="más de un millón de visitantes", tags=["fuego", "ciudad"]))
    for day in (17, 18):
        ev.append(_ev(date(y, 3, day), "Fallas: Ofrenda de flores a la Virgen", "Fiesta / desfile", ["reina", "ayuntamiento", "colon"], 3, "15:00", "01:00",
                      "Desfile por las calles de San Vicente y de la Paz hasta la Plaza de la Virgen, desde las 15:30 hasta pasada la medianoche.", tags=["desfile"]))
    ev.append(_ev(date(y, 3, 18), "Fallas: Nit del Foc (castillo de fuegos artificiales)", "Fiesta / desfile", ["america", "turia"], 3, "23:00", "02:30",
                  "Castillo de fuegos en el Paseo de la Alameda hacia la 01:30. Muy ruidoso y con muchísima gente." + RUIDO, start="01:30"))
    ev.append(_ev(date(y, 3, 19), "Fallas: la Cremà (se queman las fallas)", "Fiesta / desfile", BARRIOS, 3, "20:00", "02:00",
                  "Las fallas se queman desde las 22:00; la de la Plaza del Ayuntamiento hacia la 01:00. Fuego, petardos y calles llenas." + RUIDO))
    # Navidad y Año Nuevo
    ev.append(_ev(date(y, 1, 5), "Cabalgata de los Reyes Magos", "Fiesta / desfile", ["ayuntamiento", "colon", "san_agustin"], 3, "17:00", "21:30",
                  "La cabalgata recorre el centro por la tarde. Muchísimas familias en las aceras desde horas antes.",
                  url="https://www.visitvalencia.com/agenda-valencia", tags=["desfile"]))
    ev.append(_ev(date(y, 12, 31), "Nochevieja en la Plaza del Ayuntamiento", "Fiesta / desfile", ["ayuntamiento"], 3, "22:00", "01:30",
                  "Campanadas, música y fuegos artificiales." + RUIDO, url="https://www.visitvalencia.com/agenda-valencia"))
    # 9 d'Octubre
    ev.append(_ev(date(y, 10, 9), "9 d'Octubre: Procesión Cívica y manifestaciones", "Fiesta / desfile", ["ayuntamiento", "reina", "parterre", "san_agustin"], 3, "11:00", "21:00",
                  "Por la mañana, Procesión Cívica por el centro con tracas y petardos; por la tarde suele haber varias manifestaciones." + RUIDO,
                  url="https://www.visitvalencia.com/agenda-valencia"))
    # Batalla de Flores (último domingo de julio)
    ev.append(_ev(_last_sunday(y, 7), "Gran Fira de Juliol: Batalla de Flores", "Fiesta / desfile", ["america", "turia"], 2, "18:30", "22:00",
                  "Desfile en el Paseo de la Alameda con lanzamiento de flores.", url="https://www.visitvalencia.com/agenda-valencia", tags=["desfile"]))
    return ev


def scrape() -> list[Event]:
    t = today()
    return [e for y in (t.year, t.year + 1) for e in _year(y)]
