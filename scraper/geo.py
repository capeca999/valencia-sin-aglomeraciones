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

# Patrones habituales (no son eventos: lo que suele pasar)
PATTERNS = [
    {"zone": "mercado", "days": [6], "from": "10:00", "to": "14:00", "label": "Mercado Central y Lonja: los sábados por la mañana suele haber muchos turistas y gente comprando."},
    {"zone": "colon", "days": [5, 6], "from": "17:00", "to": "21:00", "label": "Calle Colón: tardes de viernes y sábado, mucha gente de compras."},
    {"zone": "ruzafa", "days": [5, 6], "from": "21:00", "to": "02:00", "label": "Ruzafa: noches de fin de semana con bares y terrazas llenas y ruido en la calle."},
    {"zone": "carmen", "days": [5, 6], "from": "21:00", "to": "02:00", "label": "El Carmen: noches de fin de semana con mucho ambiente y ruido."},
    {"zone": "malvarrosa", "days": [0], "from": "12:00", "to": "17:00", "label": "Paseo de la Malvarrosa: domingos a mediodía, sobre todo si hace sol."},
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
    return {k: {"name": v["name"], "lat": v["lat"], "lon": v["lon"], "r": v["r"]} for k, v in ZONES.items()}
