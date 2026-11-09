"""Calendario de fiestas con fecha fija en València (se repiten cada año).

No depende de ninguna web: son tradiciones con fechas conocidas. Las horas son las
habituales y pueden variar un poco cada año; el aviso enlaza al programa oficial.
Cada texto va en castellano, valenciano e inglés: (es, va, en).
"""
from __future__ import annotations

from datetime import date, timedelta

from ..common import Event, today, tr

SID = "fiestas"
NAME = "Calendario de fiestas de València (fechas fijas)"
FALLAS_URL = "https://www.visitvalencia.com/agenda-valencia/fallas-valencia"
AGENDA_URL = "https://www.visitvalencia.com/agenda-valencia"
RUIDO = (" Hay petardos, mucho ruido y olor a pólvora en toda la ciudad; si te afecta el ruido, lleva protección auditiva.",
         " Hi ha petards, molt de soroll i olor de pólvora per tota la ciutat; si t'afecta el soroll, porta protecció auditiva.",
         " There are firecrackers, lots of noise and the smell of gunpowder all over the city; if noise affects you, bring ear protection.")
BARRIOS = ["ayuntamiento", "san_agustin", "colon", "reina", "mercado", "carmen", "ruzafa", "parterre", "america"]
MUCHA = ("decenas de miles de personas", "desenes de milers de persones", "tens of thousands of people")


def _plus(a, b):
    return tuple(x + y for x, y in zip(a, b))


def _last_sunday(year: int, month: int) -> date:
    d = date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)
    return d - timedelta(days=(d.weekday() - 6) % 7)


def _ev(d, title, zones, level, frm, to, tip, people=MUCHA, url=FALLAS_URL, start=None, tags=None, typ="Fiesta / desfile"):
    return Event(date=d.isoformat(), title=title[0], type=typ, zones=zones, level=level, source_name=NAME, source_url=url,
                 start=start or frm, frm=frm, to=to, people=people[0], tip=tip[0], official=False, confirmed=True,
                 approx=True, sid=SID, tags=tags or ["fuego"], i18n=tr(title=title, tip=tip, people=people))


def _year(y: int) -> list[Event]:
    ev = []
    # ---- Fallas ----
    ev.append(_ev(_last_sunday(y, 2), ("Fallas: la Crida (inicio de las Fallas)", "Falles: la Crida (inici de les Falles)", "Fallas: the Crida (start of Fallas)"),
                  ["carmen"], 3, "18:30", "21:30",
                  _plus(("La Crida se celebra en las Torres de Serranos, con fuegos artificiales al final.",
                         "La Crida se celebra a les Torres de Serrans, amb focs artificials al final.",
                         "The Crida takes place at the Serranos Towers, with fireworks at the end."), RUIDO)))
    for day in range(1, 20):
        ev.append(_ev(date(y, 3, day), ("Fallas: mascletà en la Plaza del Ayuntamiento", "Falles: mascletà a la plaça de l'Ajuntament", "Fallas: mascletà in Plaza del Ayuntamiento"),
                      ["ayuntamiento", "san_agustin", "colon"], 3 if day >= 10 else 2, "12:45", "14:45",
                      _plus(("La mascletà es a las 14:00 y es MUY ruidosa (se nota en todo el centro). La plaza se llena desde una hora antes.",
                             "La mascletà és a les 14:00 i és MOLT sorollosa (es nota en tot el centre). La plaça s'ompli des d'una hora abans.",
                             "The mascletà is at 2pm and is VERY loud (you can hear it all over the centre). The square fills up an hour before."), RUIDO),
                      start="14:00"))
    for day in (14, 15, 16, 17, 18, 19):
        ev.append(_ev(date(y, 3, day), ("Semana de Fallas: TODA la ciudad llena de gente, fuego y petardos",
                                        "Setmana de Falles: TOTA la ciutat plena de gent, foc i petards",
                                        "Fallas week: the WHOLE city packed with people, fire and firecrackers"),
                      BARRIOS, 3, "", "",
                      _plus(("Es la semana más difícil del año en València: cientos de miles de personas en la calle, música y petardos en casi todos los barrios de día y de noche, calles cortadas y metro abarrotado. Si puedes, organiza estos días para salir lo justo, o pásalos fuera de la ciudad.",
                             "És la setmana més difícil de l'any a València: centenars de milers de persones al carrer, música i petards en quasi tots els barris de dia i de nit, carrers tallats i metro ple de gom a gom. Si pots, organitza estos dies per a eixir el just, o passa'ls fora de la ciutat.",
                             "It's the hardest week of the year in Valencia: hundreds of thousands of people on the streets, music and firecrackers in almost every neighbourhood day and night, closed streets and packed metros. If you can, plan these days to go out as little as possible, or spend them outside the city."), RUIDO),
                      people=("más de un millón de visitantes", "més d'un milió de visitants", "over a million visitors"), tags=["fuego", "ciudad"]))
    for day in (17, 18):
        ev.append(_ev(date(y, 3, day), ("Fallas: Ofrenda de flores a la Virgen", "Falles: Ofrena de flors a la Mare de Déu", "Fallas: Flower Offering to the Virgin"),
                      ["reina", "ayuntamiento", "colon"], 3, "15:00", "01:00",
                      ("Desfile por las calles de San Vicente y de la Paz hasta la Plaza de la Virgen, desde las 15:30 hasta pasada la medianoche.",
                       "Desfilada pels carrers de Sant Vicent i de la Pau fins a la plaça de la Mare de Déu, des de les 15:30 fins passada la mitjanit.",
                       "Parade along Calle San Vicente and Calle de la Paz to Plaza de la Virgen, from 3:30pm until after midnight."),
                      tags=["desfile"]))
    ev.append(_ev(date(y, 3, 18), ("Fallas: Nit del Foc (castillo de fuegos artificiales)", "Falles: Nit del Foc (castell de focs artificials)", "Fallas: Nit del Foc (fireworks display)"),
                  ["america", "turia"], 3, "23:00", "02:30",
                  _plus(("Castillo de fuegos en el Paseo de la Alameda hacia la 01:30. Muy ruidoso y con muchísima gente.",
                         "Castell de focs al passeig de l'Albereda cap a la 01:30. Molt sorollós i amb moltíssima gent.",
                         "Fireworks display on the Paseo de la Alameda around 1:30am. Very loud and extremely crowded."), RUIDO),
                  start="01:30"))
    ev.append(_ev(date(y, 3, 19), ("Fallas: la Cremà (se queman las fallas)", "Falles: la Cremà (es cremen les falles)", "Fallas: the Cremà (the fallas are burned)"),
                  BARRIOS, 3, "20:00", "02:00",
                  _plus(("Las fallas se queman desde las 22:00; la de la Plaza del Ayuntamiento hacia la 01:00. Fuego, petardos y calles llenas.",
                         "Les falles es cremen des de les 22:00; la de la plaça de l'Ajuntament cap a la 01:00. Foc, petards i carrers plens.",
                         "The fallas are burned from 10pm; the one in Plaza del Ayuntamiento around 1am. Fire, firecrackers and packed streets."), RUIDO)))
    # ---- Navidad, Reyes, Año Nuevo ----
    ev.append(_ev(date(y, 1, 5), ("Cabalgata de los Reyes Magos", "Cavalcada dels Reis Mags", "Three Kings Parade"),
                  ["ayuntamiento", "colon", "san_agustin"], 3, "17:00", "21:30",
                  ("La cabalgata recorre el centro por la tarde. Muchísimas familias en las aceras desde horas antes.",
                   "La cavalcada recorre el centre per la vesprada. Moltíssimes famílies a les voreres des d'hores abans.",
                   "The parade goes through the centre in the afternoon. Lots of families line the pavements hours beforehand."),
                  url=AGENDA_URL, tags=["desfile"]))
    ev.append(_ev(date(y, 12, 31), ("Nochevieja en la Plaza del Ayuntamiento", "Nit de Cap d'Any a la plaça de l'Ajuntament", "New Year's Eve in Plaza del Ayuntamiento"),
                  ["ayuntamiento"], 3, "22:00", "01:30",
                  _plus(("Campanadas, música y fuegos artificiales.", "Campanades, música i focs artificials.", "Midnight bells, music and fireworks."), RUIDO),
                  url=AGENDA_URL))
    # ---- 9 d'Octubre ----
    ev.append(_ev(date(y, 10, 9), ("9 d'Octubre: Procesión Cívica y manifestaciones", "9 d'Octubre: Processó Cívica i manifestacions", "9 d'Octubre: Civic Procession and demonstrations"),
                  ["ayuntamiento", "reina", "parterre", "san_agustin"], 3, "11:00", "21:00",
                  _plus(("Por la mañana, Procesión Cívica por el centro con tracas y petardos; por la tarde suele haber varias manifestaciones.",
                         "Pel matí, Processó Cívica pel centre amb traques i petards; per la vesprada sol haver-hi diverses manifestacions.",
                         "In the morning, the Civic Procession goes through the centre with firecracker strings; in the afternoon there are usually several demonstrations."), RUIDO),
                  url=AGENDA_URL))
    # ---- Batalla de Flores (último domingo de julio) ----
    ev.append(_ev(_last_sunday(y, 7), ("Gran Fira de Juliol: Batalla de Flores", "Gran Fira de Juliol: Batalla de Flors", "July Fair: Battle of Flowers"),
                  ["america", "turia"], 2, "18:30", "22:00",
                  ("Desfile en el Paseo de la Alameda con lanzamiento de flores.", "Desfilada al passeig de l'Albereda amb llançament de flors.", "Parade on the Paseo de la Alameda where flowers are thrown."),
                  url=AGENDA_URL, tags=["desfile"]))
    return ev


def scrape() -> list[Event]:
    t = today()
    return [e for y in (t.year, t.year + 1) for e in _year(y)]
