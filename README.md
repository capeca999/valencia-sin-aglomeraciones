# Valencia sin aglomeraciones

Web que avisa de **dónde y cuándo va a haber mucha gente en Valencia**, pensada para personas autistas o con sensibilidad sensorial: colores suaves, sin animaciones, lenguaje claro y el nivel de gente indicado con texto (no solo con color).

**Web:** https://capeca999.github.io/valencia-sin-aglomeraciones/

## Cómo funciona

Cada mañana, GitHub Actions ejecuta `scraper/` y revisa estas fuentes oficiales:

| Fuente | Qué aporta |
|---|---|
| Ajuntament de València · Movilidad «Incidencias y previsiones» | Afecciones de tráfico por conciertos, partidos, carreras, desfiles y manifestaciones |
| Ajuntament de València · Noticias de movilidad | Dispositivos especiales de tráfico |
| Geoportal del Ajuntament (en el navegador) | Calles cortadas en tiempo real |
| Roig Arena (web oficial) | Conciertos, Valencia Basket y espectáculos |
| Visit València | Calendario del Valencia Basket |
| LaLiga | Partidos en Mestalla y en el Ciutat de València |

El resultado se guarda en `docs/data/events.json` y se publica con GitHub Pages. Si una fuente falla un día, se conservan sus datos anteriores.

## Avisos al móvil

Instala la app **ntfy** y suscríbete al tema que aparece en `config.json`. Solo llega aviso los días con «Mucha gente» o más.

## Añadir un evento a mano

Edita `docs/data/manual.json` (por ejemplo, una manifestación anunciada en prensa que aún no sale en las fuentes oficiales).

## Ejecutar en local

```bash
pip install -r requirements.txt
python -m scraper.main          # VSA_DEBUG=1 guarda el HTML descargado en debug/
python -m http.server -d docs   # y abre http://localhost:8000
```
