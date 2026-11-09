"""Utilidades compartidas: descargas, fechas y modelo de evento."""
from __future__ import annotations

import os
import re
import time
import unicodedata
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

TZ = ZoneInfo("Europe/Madrid")
ROOT = Path(__file__).resolve().parent.parent
DEBUG_DIR = ROOT / "debug"
DEBUG = os.environ.get("VSA_DEBUG", "0") == "1"

HEADERS = {
    "User-Agent": "ValenciaSinAglomeraciones/1.0 (+https://github.com/capeca999/valencia-sin-aglomeraciones)",
    "Accept-Language": "es-ES,es;q=0.9,ca;q=0.8",
}

_session = requests.Session()
_session.headers.update(HEADERS)


BROWSER = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36 ValenciaSinAglomeraciones/1.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9",
}


def fetch(url: str, *, name: str | None = None, tries: int = 3, timeout: int = 30) -> str:
    """Descarga una URL como texto, con reintentos. Si VSA_DEBUG=1 guarda el HTML."""
    last = None
    for i in range(tries):
        try:
            headers = BROWSER if (i > 0 or "valencia.es" in url) else None
            r = _session.get(url, timeout=timeout, headers=headers)
            if r.status_code == 403 and DEBUG and name:
                DEBUG_DIR.mkdir(exist_ok=True)
                (DEBUG_DIR / f"{name}_403.html").write_text(r.text[:20000], encoding="utf-8")
            r.raise_for_status()
            r.encoding = r.encoding or "utf-8"
            text = r.text
            if DEBUG and name:
                DEBUG_DIR.mkdir(exist_ok=True)
                (DEBUG_DIR / f"{name}.html").write_text(text, encoding="utf-8")
            return text
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"No se pudo descargar {url}: {last}")


def now() -> datetime:
    return datetime.now(TZ)


def today() -> date:
    return now().date()


def norm(s: str) -> str:
    """Minúsculas sin tildes, para comparar textos."""
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("*", "")).strip()


def hm(t: str | None) -> str:
    """'20.30' / '20:30' / '9' -> '20:30'."""
    if not t:
        return ""
    m = re.match(r"(\d{1,2})(?:[:.h](\d{2}))?", t.strip())
    if not m:
        return ""
    h, mi = int(m.group(1)), int(m.group(2) or 0)
    if h > 24 or mi > 59:
        return ""
    return f"{h % 24:02d}:{mi:02d}"


def shift(t: str, minutes: int) -> str:
    if not t:
        return ""
    h, m = map(int, t.split(":"))
    total = (h * 60 + m + minutes) % (24 * 60)
    return f"{total // 60:02d}:{total % 60:02d}"


@dataclass
class Event:
    date: str                     # AAAA-MM-DD
    title: str
    type: str                     # Concierto, Fútbol, Baloncesto, Manifestación, Carrera, Aviso...
    zones: list[str]
    level: int                    # 1 algo de gente, 2 mucha, 3 muchísima
    source_name: str
    source_url: str
    start: str = ""               # hora de inicio HH:MM
    frm: str = ""                 # franja a evitar, desde
    to: str = ""                  # franja a evitar, hasta
    people: str = ""
    tip: str = ""
    official: bool = True
    confirmed: bool = True
    approx: bool = False
    raw: str = ""                 # texto original (avisos del Ayuntamiento)
    tags: list[str] = field(default_factory=list)
    sid: str = ""                 # id de la fuente que lo generó

    def key(self) -> str:
        return f"{self.date}|{norm(self.title)[:40]}"

    def to_json(self) -> dict:
        d = asdict(self)
        d["from"] = d.pop("frm")
        d["source"] = {"name": d.pop("source_name"), "url": d.pop("source_url")}
        return d


def window(start: str, duration_min: int, before: int = 75, after: int = 45) -> tuple[str, str]:
    """Franja a evitar: llegada del público + evento + salida."""
    if not start:
        return "", ""
    return shift(start, -before), shift(start, duration_min + after)


def in_range(d: date, days_ahead: int = 60) -> bool:
    t = today()
    return t - timedelta(days=1) <= d <= t + timedelta(days=days_ahead)
