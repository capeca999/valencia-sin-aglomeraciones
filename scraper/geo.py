"""Lugares de Valencia donde se concentra gente, y cómo reconocerlos en un texto."""
from __future__ import annotations

import re

from .common import norm

# id: nombre, lat, lon, radio en metros, palabras clave (sin tildes, minúsculas)
ZONES: dict[str, dict] = {
    "roig":        {"name": "Roig Arena", "lat": 39.4492, "lon": -0.3643, "r": 450,
                    "kw": ["roig arena", "auditorio roig", "auditorium hall", "bomber ramon duart", "font de sant lluis", "fonteta"]},
    "mestalla":    {"name": "Estadio de Mestalla", "lat": 39.4746, "lon": -0.3583, "r": 550,
                    "kw": ["mestalla"]},
    "ciutat":      {"name": "Estadio Ciutat de València", "lat": 39.4947, "lon": -0.3644, "r": 500,
                    "kw": ["estadio ciutat de valencia", "estadi ciutat de valencia", "estadio del levante", "orriols"]},
    "cac":         {"name": "Ciudad de las Artes y las Ciencias", "lat": 39.4547, "lon": -0.3505, "r": 600,
                    "kw": ["ciudad de las artes", "ciutat de les arts", "museo principe felipe", "museu de les ciencies", "hemisferic", "agora", "palau de les arts", "umbracle"]},
    "marina":      {"name": "La Marina / Puerto", "lat": 39.4600, "lon": -0.3240, "r": 550,
                    "kw": ["la marina", "marina de valencia", "marina sur", "veles e vents", "tinglado", "puerto de valencia"]},
    "tarongers":   {"name": "Av. Tarongers / Universidades", "lat": 39.4790, "lon": -0.3420, "r": 550,
                    "kw": ["tarongers", "naranjos", "ciudad politecnica", "upv"]},
    "blasco":      {"name": "Av. Blasco Ibáñez", "lat": 39.4757, "lon": -0.3480, "r": 450,
                    "kw": ["blasco ibanez"]},
    "malvarrosa":  {"name": "Paseo de la Malvarrosa", "lat": 39.4780, "lon": -0.3245, "r": 500,
                    "kw": ["malvarrosa", "malva-rosa", "paseo maritimo", "passeig maritim", "las arenas", "eugenia vines"]},
    "ayuntamiento": {"name": "Plaza del Ayuntamiento", "lat": 39.4697, "lon": -0.3763, "r": 380,
                    "kw": ["plaza del ayuntamiento", "placa de l'ajuntament", "plaza ayuntamiento", "placa ajuntament", "marques de sotelo", "mascleta"]},
    "san_agustin": {"name": "Plaza San Agustín / Xàtiva", "lat": 39.4667, "lon": -0.3780, "r": 300,
                    "kw": ["san agustin", "sant agusti", "calle xativa", "carrer de xativa", "estacion del norte", "calle hospital"]},
    "colon":       {"name": "Calle Colón / Porta de la Mar", "lat": 39.4706, "lon": -0.3710, "r": 330,
                    "kw": ["colon", "porta de la mar", "puerta del mar", "plaza de los pinazo", "placa dels pinazo", "delegacion del gobierno"]},
    "parterre":    {"name": "Parterre / Plaza Alfonso el Magnánimo", "lat": 39.4719, "lon": -0.3712, "r": 250,
                    "kw": ["parterre", "alfonso el magnanimo", "alfons el magnanim", "glorieta"]},
    "america":     {"name": "Plaza de América / Albereda", "lat": 39.4690, "lon": -0.3650, "r": 350,
                    "kw": ["plaza de america", "placa d'america", "albereda", "alameda", "puente de las flores", "pont de les flors", "pont de l'exposicio", "puente de la exposicion"]},
    "reina":       {"name": "Plaza de la Reina / Catedral", "lat": 39.4748, "lon": -0.3756, "r": 260,
                    "kw": ["plaza de la reina", "placa de la reina", "catedral", "plaza de la virgen", "placa de la mare de deu", "san vicente martir", "sant vicent martir"]},
    "mercado":     {"name": "Mercado Central / Lonja", "lat": 39.4736, "lon": -0.3790, "r": 260,
                    "kw": ["mercado central", "mercat central", "lonja", "llotja", "plaza del mercado", "placa del mercat"]},
    "carmen":      {"name": "El Carmen / Torres de Serranos", "lat": 39.4785, "lon": -0.3795, "r": 360,
                    "kw": ["el carmen", "el carme", "torres de serranos", "torres de quart", "plaza del tossal", "caballeros"]},
    "ruzafa":      {"name": "Ruzafa", "lat": 39.4625, "lon": -0.3740, "r": 400,
                    "kw": ["ruzafa", "russafa", "mercado de ruzafa"]},
    "viveros":     {"name": "Jardines de Viveros", "lat": 39.4795, "lon": -0.3665, "r": 380,
                    "kw": ["viveros", "vivers", "jardines del real", "jardins del real"]},
    "turia":       {"name": "Jardín del Turia (tramo central)", "lat": 39.4720, "lon": -0.3640, "r": 600,
                    "kw": ["antiguo cauce", "jardin del turia", "jardi del turia", "cauce del rio"]},
    "campanar":    {"name": "Av. Campanar (Conselleria de Educación)", "lat": 39.4815, "lon": -0.3935, "r": 300,
                    "kw": ["conselleria de educacion", "conselleria d'educacio", "avenida de campanar", "av. campanar", "avinguda de campanar"]},
    "feria":       {"name": "Feria Valencia", "lat": 39.5055, "lon": -0.4205, "r": 550,
                    "kw": ["feria valencia", "fira valencia", "recinto ferial"]},
}

# Nombres de las zonas en valenciano e inglés
NAMES = {
    "mestalla": ("Estadi de Mestalla", "Mestalla Stadium"),
    "ciutat": ("Estadi Ciutat de València", "Ciutat de València Stadium"),
    "cac": ("Ciutat de les Arts i les Ciències", "City of Arts and Sciences"),
    "marina": ("La Marina / Port", "La Marina / Port"),
    "tarongers": ("Av. dels Tarongers / Universitats", "Av. Tarongers / Universities"),
    "blasco": ("Av. de Blasco Ibáñez", "Av. Blasco Ibáñez"),
    "malvarrosa": ("Passeig de la Malva-rosa", "Malvarrosa promenade"),
    "ayuntamiento": ("Plaça de l'Ajuntament", "City Hall Square (Plaza del Ayuntamiento)"),
    "san_agustin": ("Plaça de Sant Agustí / Xàtiva", "Plaza San Agustín / Xàtiva"),
    "colon": ("Carrer de Colón / Porta de la Mar", "Calle Colón / Porta de la Mar"),
    "parterre": ("Parterre / Plaça d'Alfons el Magnànim", "Parterre / Plaza Alfonso el Magnánimo"),
    "america": ("Plaça d'Amèrica / Albereda", "Plaza de América / Alameda"),
    "reina": ("Plaça de la Reina / Catedral", "Plaza de la Reina / Cathedral"),
    "mercado": ("Mercat Central / Llotja", "Central Market / Lonja"),
    "carmen": ("El Carme / Torres de Serrans", "El Carmen / Serranos Towers"),
    "ruzafa": ("Russafa", "Ruzafa"),
    "viveros": ("Jardins de Vivers", "Viveros Gardens"),
    "turia": ("Jardí del Túria (tram central)", "Turia Gardens (central section)"),
    "feria": ("Fira València", "Feria Valencia"),
    "campanar": ("Av. de Campanar (Conselleria d'Educació)", "Av. Campanar (Regional Education Department)"),
}

# Patrones habituales (no son eventos: lo que suele pasar)
PATTERNS = [
    {"zone": "mercado", "days": [6], "from": "10:00", "to": "14:00",
     "label": "Mercado Central y Lonja: los sábados por la mañana suele haber muchos turistas y gente comprando.",
     "i18n": {"va": {"label": "Mercat Central i Llotja: els dissabtes pel matí sol haver-hi molts turistes i gent comprant."},
              "en": {"label": "Central Market and Lonja: on Saturday mornings there are usually lots of tourists and shoppers."}}},
    {"zone": "colon", "days": [5, 6], "from": "17:00", "to": "21:00",
     "label": "Calle Colón: tardes de viernes y sábado, mucha gente de compras.",
     "i18n": {"va": {"label": "Carrer de Colón: vesprades de divendres i dissabte, molta gent de compres."},
              "en": {"label": "Calle Colón: Friday and Saturday afternoons, lots of people shopping."}}},
    {"zone": "ruzafa", "days": [5, 6], "from": "21:00", "to": "02:00",
     "label": "Ruzafa: noches de fin de semana con bares y terrazas llenas y ruido en la calle.",
     "i18n": {"va": {"label": "Russafa: nits de cap de setmana amb bars i terrasses plens i soroll al carrer."},
              "en": {"label": "Ruzafa: weekend nights with packed bars and terraces and noise in the street."}}},
    {"zone": "carmen", "days": [5, 6], "from": "21:00", "to": "02:00",
     "label": "El Carmen: noches de fin de semana con mucho ambiente y ruido.",
     "i18n": {"va": {"label": "El Carme: nits de cap de setmana amb molt d'ambient i soroll."},
              "en": {"label": "El Carmen: busy, noisy weekend nights."}}},
    {"zone": "malvarrosa", "days": [0], "from": "12:00", "to": "17:00",
     "label": "Paseo de la Malvarrosa: domingos a mediodía, sobre todo si hace sol.",
     "i18n": {"va": {"label": "Passeig de la Malva-rosa: diumenges a migdia, sobretot si fa sol."},
              "en": {"label": "Malvarrosa promenade: Sundays around midday, especially when it's sunny."}}},
]


def find_zones(text: str) -> list[str]:
    """Devuelve las zonas mencionadas en un texto, en orden de aparición."""
    t = norm(text)
    t = re.sub(r"\bmarina (alta|baixa|baja)\b", " ", t)  # comarcas, no La Marina de València
    hits = []
    for zid, z in ZONES.items():
        pos = min((m.start() for k in z["kw"] for m in [re.search(r"\b" + re.escape(k) + r"\b", t)] if m), default=-1)
        if pos >= 0:
            hits.append((pos, zid))
    return [z for _, z in sorted(hits)]


def zones_json() -> dict:
    out = {}
    for k, v in ZONES.items():
        z = {"name": v["name"], "lat": v["lat"], "lon": v["lon"], "r": v["r"]}
        if k in NAMES:
            z["i18n"] = {"va": {"name": NAMES[k][0]}, "en": {"name": NAMES[k][1]}}
        out[k] = z
    return out
