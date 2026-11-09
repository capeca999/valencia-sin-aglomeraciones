"""Roig Arena · web oficial del recinto (conciertos, Valencia Basket y espectáculos).

Las fichas de evento tienen este formato:
  Day 31/01/2027 · Time 20:30 · Location Roig Arena | Auditorium Hall | Exterior ...
"""
from __future__ import annotations

import re
import time
from datetime import date, datetime, timedelta
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..common import Event, clean, fetch, hm, in_range, norm, today, window

SID = "roig_arena"
NAME = "Roig Arena (web oficial)"
BASE = "https://www.roigarena.com"
LISTING = BASE + "/eventos/?page={}"
MAX_PAGES = 15
EVENT_LINK = re.compile(r"/(?:en/|es/)?(?:event|evento|eventos)/[a-z0-9\-]+/?$")
DMY = re.compile(r"(\d{2})/(\d{2})/(\d{4})")
TIME = re.compile(r"\b(\d{1,2}:\d{2})\b")
MAX_DETAILS = 100


def _slug_date(url: str) -> date | None:
    m = re.search(r"-(\d{8})/?$", url)
    if not m:
        return None
    s = m.group(1)
    for fmt in ("%Y%m%d", "%Y%d%m"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _detail(url: str) -> dict:
    html = fetch(url)
    soup = BeautifulSoup(html, "lxml")
    for s in soup(["script", "style", "noscript"]):
        s.decompose()
    h1 = soup.find("h1")
    title = clean(h1.get_text(" ")) if h1 else ""
    lines = [clean(x) for x in soup.get_text("\n").split("\n")]
    lines = [x for x in lines if x]
    info = {"title": title}
    for i, ln in enumerate(lines[:400]):
        key = norm(ln)
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if key in ("dia", "day", "fecha") and "date" not in info:
            m = DMY.search(nxt)
            if m:
                info["date"] = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        elif key in ("hora", "time", "horario") and "time" not in info:
            m = TIME.search(nxt)
            if m:
                info["time"] = hm(m.group(1))
        elif key in ("ubicacion", "location", "lugar", "ubicacio") and "loc" not in info:
            info["loc"] = nxt
    if "date" not in info:
        m = DMY.search(" ".join(lines[:200]))
        if m:
            info["date"] = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    return info


def _make(title: str, d: date, start: str, loc: str, url: str) -> Event:
    t, l = norm(title), norm(loc)
    small = any(k in l for k in ("auditori", "hall", "sala", "exterior"))
    if re.search(r"\b(vbc|valencia basket|valencia bc)\b", t) or " vs " in t:
        typ, dur = "Baloncesto", 120
        people = "unas 12.000 personas" if not small else "aforo mediano"
    else:
        typ, dur = "Concierto / espectáculo", 150
        people = "hasta 15.000 personas" if not small else "hasta 2.000 personas"
    lvl = 1 if small else 2
    frm, to = window(start, dur)
    where = "Auditorio del Roig Arena" if small else "Roig Arena"
    return Event(
        date=d.isoformat(), title=title, type=typ, zones=["roig"], level=lvl,
        source_name=NAME, source_url=url, start=start, frm=frm, to=to, people=people,
        approx=True, sid=SID,
        tip=(f"Evita el entorno del {where} (Quatre Carreres) y el transporte hacia allí en esa franja. "
             "La salida del público suele ser el momento más agobiante."),
    )


def scrape() -> list[Event]:
    links: dict[str, str] = {}
    listing_hits: dict[str, tuple] = {}
    errors = []
    for page in range(1, MAX_PAGES + 1):
        try:
            html = fetch(LISTING.format(page), name=f"{SID}_list_{page}" if page <= 2 else None)
        except Exception as e:  # noqa: BLE001
            errors.append(str(e))
            break
        soup = BeautifulSoup(html, "lxml")
        new = 0
        for a in soup.find_all("a", href=True):
            href = urljoin(BASE, a["href"].split("?")[0])
            if "roigarena.com" in href and EVENT_LINK.search(href) and href not in links:
                txt = clean(a.get_text(" "))
                links[href] = txt
                new += 1
                m, tm = DMY.search(txt), TIME.search(txt)
                if m:
                    listing_hits[href] = (date(int(m.group(3)), int(m.group(2)), int(m.group(1))), hm(tm.group(1)) if tm else "")
        if not new:
            break
        dates = [d for d in (_slug_date(u) for u in links) if d]
        if dates and max(dates) > today().replace(day=1) + timedelta(days=75):
            break
        time.sleep(0.4)
    if not links and errors:
        raise RuntimeError("; ".join(errors))

    events: list[Event] = []
    done = 0
    t0 = today()
    for url, txt in links.items():
        d0 = listing_hits.get(url, (None, ""))[0] or _slug_date(url)
        if d0 and not in_range(d0):
            continue
        if done >= MAX_DETAILS:
            break
        try:
            info = _detail(url)
            done += 1
            time.sleep(0.4)
        except Exception:  # noqa: BLE001
            info = {}
        d = info.get("date") or d0
        if not d or not in_range(d) or d < t0:
            continue
        title = info.get("title") or re.sub(DMY, "", txt).strip() or url.rstrip("/").split("/")[-1]
        start = info.get("time") or listing_hits.get(url, (None, ""))[1]
        events.append(_make(title, d, start, info.get("loc", ""), url))
    return events
