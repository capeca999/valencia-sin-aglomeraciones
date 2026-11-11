(function () {
  "use strict";
  // Clave pública de CARTO Basemaps (gratis para uso no comercial). Va en el navegador: es normal que sea visible.
  // Restríngela a tu dominio (capeca999.github.io) en el panel de CARTO.
  var CARTO_KEY = "cb1_559w_1_188a2836d59cdf2f50ac30a1";
  // Usuario de Buy Me a Coffee (buymeacoffee.com/USUARIO). Vacío = no se muestra el botón.
  var BMC_USER = "";
  // Correo de contacto, partido en dos para que los robots que recogen correos lo encuentren peor.
  // Vacío = no se muestra la sección de contacto.
  var CONTACT = { user: "pinazogunafrancisco", domain: "gmail.com" };
  var LIVE_URL = "https://geoportal.valencia.es/server/rest/services/OPENDATA/Trafico/MapServer/192/query?where=1%3D1&outFields=*&outSR=4326&f=geojson";

  var store = {
    get: function (k, d) { try { var v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
    set: function (k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  };
  function $(id) { return document.getElementById(id); }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function ymd(d) { return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0"); }
  function parse(s) { var p = s.split("-").map(Number); return new Date(p[0], p[1] - 1, p[2]); }
  function cap(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : s; }
  function css(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }

  // ---------- Idioma ----------
  function pickLang() {
    var q = (location.search.match(/[?&]lang=(es|va|en)\b/) || [])[1];
    if (q) return q;
    var s = store.get("vsa-lang", null);
    if (s && I18N[s]) return s;
    var n = (navigator.language || "es").toLowerCase();
    return /^(ca|va)/.test(n) ? "va" : /^en/.test(n) ? "en" : "es";
  }
  var LANG = pickLang();
  function T(key, vars) {
    var dict = I18N[LANG], v = key.split(".").reduce(function (o, k) { return o == null ? o : o[k]; }, dict);
    if (v == null) v = key.split(".").reduce(function (o, k) { return o == null ? o : o[k]; }, I18N.es);
    if (typeof v !== "string") return v;
    return v.replace(/\{(\w+)\}/g, function (_, k) { return vars && vars[k] != null ? vars[k] : ""; });
  }
  // Campo traducido de un dato (evento, zona, lugar): i18n.<idioma>.<campo> o el original en castellano
  function tx(o, field) {
    if (!o) return "";
    var t = o.i18n && o.i18n[LANG] && o.i18n[LANG][field];
    return t || o[field] || "";
  }
  function typeName(t) { return (I18N[LANG].types || {})[t] || t; }
  function longDate(d) { return I18N[LANG].longDate(T("wd")[d.getDay()], d.getDate(), T("mo")[d.getMonth()]); }
  function shortDate(d) { return I18N[LANG].shortDate(d.getDate(), T("mo")[d.getMonth()]); }
  function applyStatic() {
    document.documentElement.lang = T("htmlLang");
    document.title = T("title");
    document.querySelectorAll("[data-i18n]").forEach(function (el) { el.textContent = T(el.getAttribute("data-i18n")); });
    document.querySelectorAll("[data-i18n-html]").forEach(function (el) { el.innerHTML = T(el.getAttribute("data-i18n-html")); });
    document.querySelectorAll("[data-i18n-aria]").forEach(function (el) { el.setAttribute("aria-label", T(el.getAttribute("data-i18n-aria"))); });
    $("langGroup").setAttribute("aria-label", T("language"));
    document.querySelectorAll(".lang").forEach(function (b) { b.setAttribute("aria-pressed", b.dataset.lang === LANG ? "true" : "false"); });
    $("phoneLang").hidden = !T("phoneLang");
  }

  // Zonas agrupadas por barrios para "Mis sitios"
  var AREAS = {
    centro: ["ayuntamiento", "san_agustin", "colon", "reina", "mercado", "carmen", "parterre"],
    ruzafa: ["ruzafa", "america"],
    turia: ["turia", "viveros"],
    mestalla: ["mestalla", "blasco", "tarongers"],
    sur: ["roig", "cac"],
    maritimo: ["marina", "malvarrosa"],
    orriols: ["ciutat"],
    oeste: ["campanar", "feria"]
  };
  var today = new Date(); today.setHours(0, 0, 0, 0);
  var TODAY = ymd(today);
  var DATA = null;
  var QUIET = { hours: [], places: [] };
  var state = {
    mine: store.get("vsa-mine", []), onlyMine: store.get("vsa-onlymine", false),
    a11y: store.get("vsa-a11y", false), dys: store.get("vsa-dys", false), simple: store.get("vsa-simple", false), size: store.get("vsa-size", 1),
    quiet: store.get("vsa-quiet", true), noise: store.get("vsa-noise", false),
    minLevel: store.get("vsa-small", false) ? 1 : 2, patterns: store.get("vsa-patterns", true),
    live: store.get("vsa-live", false), selected: TODAY, weekStart: 0
  };

  function isCityWide(e) { return (e.tags || []).indexOf("ciudad") >= 0 || (e.type === "Huelga" && !(e.zones || []).length); }
  function areasOf(e) {
    if (isCityWide(e)) return Object.keys(AREAS);
    var zs = (e.zones || []).slice();
    // eventos situados por puntos (Geoportal): zona más cercana a menos de 1,2 km
    (e.geo || []).forEach(function (pt) {
      var best = null, bd = 1200;
      Object.keys(DATA.zones).forEach(function (z) { var Z = DATA.zones[z], d = dist(pt[0], pt[1], Z.lat, Z.lon); if (d < bd) { bd = d; best = z; } });
      if (best) zs.push(best);
    });
    return Object.keys(AREAS).filter(function (a) { return AREAS[a].some(function (z) { return zs.indexOf(z) >= 0; }); });
  }
  function isMine(e) { return state.mine.length > 0 && areasOf(e).some(function (a) { return state.mine.indexOf(a) >= 0; }); }
  function eventsOn(date) {
    return DATA.events.filter(function (e) {
      return e.date === date && e.level >= state.minLevel && (!state.onlyMine || !state.mine.length || isMine(e));
    });
  }
  function patternsOn(date) {
    if (!state.patterns) return [];
    var wd = parse(date).getDay();
    return DATA.patterns.filter(function (p) { return p.days.indexOf(wd) >= 0; });
  }
  function pictoKey(e) {
    var t = e.tags || [];
    if (t.indexOf("ciudad") >= 0 || t.indexOf("fuego") >= 0) return /mascl|petard/i.test(e.title) ? "petardo" : "fuegos";
    var m = { "Fútbol": "futbol", "Baloncesto": "baloncesto", "Concierto": "concierto", "Concierto / espectáculo": "concierto",
      "Manifestación": "manifestacion", "Huelga": "huelga", "Carrera": "carrera", "Fiesta / desfile": "desfile", "Feria": "feria", "Turismo": "crucero" };
    return m[e.type] || "gente";
  }
  // Los pictogramas acompañan a un texto que ya dice lo mismo: alt vacío para no repetirlo al lector de pantalla
  function picto(key, cls) {
    return '<img class="picto' + (cls ? " " + cls : "") + '" src="pictos/' + key + '.png" alt="" width="56" height="56" loading="lazy">';
  }
  function tagsOn(date) {
    var t = {};
    DATA.events.forEach(function (e) { if (e.date === date) (e.tags || []).forEach(function (x) { t[x] = true; }); });
    return t;
  }
  function levelOn(date) { return eventsOn(date).reduce(function (m, e) { return Math.max(m, e.level); }, 0); }
  function timeText(e) {
    if (e.from) return e.from + "–" + e.to + (e.approx ? " " + T("approx") : "");
    if (e.start) return T("fromTime", { t: e.start });
    return T("noTime");
  }
  function zoneName(z) { return tx(DATA.zones[z], "name"); }
  function zoneNames(e) {
    var n = (e.zones || []).filter(function (z) { return DATA.zones[z]; }).map(zoneName);
    if (n.length) return n.join(", ");
    if (e.type === "Huelga") return T("wholeCity");
    return (e.geo || []).length ? T("markedOnMap") : T("locInText");
  }
  function srcLink(name, url, prefix) {
    return url ? '<a href="' + esc(url) + '" target="_blank" rel="noopener">' + esc(prefix + name) + "</a>" : '<span class="sub">' + esc(prefix + name) + "</span>";
  }

  // ---------- Estado de hoy ----------
  function renderStatus() {
    var evs = eventsOn(TODAY), lvl = levelOn(TODAY), tg = tagsOn(TODAY);
    $("status").dataset.level = lvl;
    $("status").classList.toggle("fire", !!tg.fuego);
    $("statusDate").textContent = T("todayComma", { d: longDate(today) });
    $("statusPicto").src = "pictos/" + (evs.length ? pictoKey(evs.slice().sort(function (a, b) { return b.level - a.level; })[0]) : "contento") + ".png";
    if (!evs.length) {
      $("statusTitle").textContent = T("calmTitle");
      $("statusText").textContent = T("calmText");
    } else {
      $("statusTitle").textContent = tg.ciudad ? T("todayCity") : (tg.fuego ? "🔥 " : "") + T("todayLevel", { l: T("levels")[lvl].toLowerCase() });
      $("statusText").innerHTML = evs.map(function (e) { return esc(T("avoid")) + " <strong>" + esc(zoneNames(e)) + "</strong> · " + esc(timeText(e)); }).join("<br>");
    }
    var mb = $("mineBox");
    if (state.mine.length) {
      var mineEvs = DATA.events.filter(function (e) { return e.date === TODAY && e.level >= state.minLevel && isMine(e); });
      mb.hidden = false;
      mb.classList.toggle("calm", !mineEvs.length);
      mb.innerHTML = mineEvs.length
        ? '<strong class="h">★ ' + esc(T("mineToday")) + "</strong>" + mineEvs.map(function (e) { return "<span>" + esc(tx(e, "title")) + " · " + esc(timeText(e)) + "</span>"; }).join("")
        : '<strong class="h">★ ' + esc(T("mineCalm")) + "</strong>";
    } else mb.hidden = true;
    var nx = DATA.events.filter(function (e) { return e.date > TODAY && e.level >= state.minLevel && (!state.onlyMine || !state.mine.length || isMine(e)); })[0];
    var box = $("next");
    if (nx) {
      box.hidden = false;
      box.innerHTML = '<span class="sub">' + esc(T("nextAlert")) + "</span><strong>" + esc(cap(longDate(parse(nx.date)))) + "</strong><span>" +
        esc(zoneNames(nx)) + " · " + esc(timeText(nx)) + '</span><button class="link" id="goNext">' + esc(T("seeDay")) + "</button>";
      $("goNext").onclick = function () { select(nx.date); $("dayTitle").focus(); };
    } else box.hidden = true;
  }

  // ---------- Calendario ----------
  function renderStrip() {
    var strip = $("strip");
    var start = new Date(today); start.setDate(start.getDate() + state.weekStart * 7);
    strip.innerHTML = "";
    for (var i = 0; i < 7; i++) {
      var d = new Date(start); d.setDate(d.getDate() + i);
      var key = ymd(d), l = levelOn(key), tg = tagsOn(key);
      var b = document.createElement("button");
      var mineHere = state.mine.length && eventsOn(key).some(isMine);
      b.className = "day" + (key === TODAY ? " today" : "") + (tg.fuego ? " fire" : "") + (tg.ciudad ? " city" : "") + (mineHere ? " mine-day" : "");
      b.setAttribute("aria-pressed", key === state.selected ? "true" : "false");
      var lbl = longDate(d) + ": " + (tg.ciudad ? T("fireCity") : T("levels")[l] + (tg.fuego ? ", " + T("fire") : ""));
      b.setAttribute("aria-label", (key === TODAY ? T("todayShort") + ", " : "") + lbl + (mineHere ? ", " + T("mineDay") : ""));
      b.innerHTML = '<span class="wd" aria-hidden="true">' + esc(key === TODAY ? T("todayShort") : T("wdShort")[d.getDay()]) + '</span><span class="dn" aria-hidden="true">' + d.getDate() +
        '</span><span class="mo" aria-hidden="true">' + esc(T("moShort")[d.getMonth()]) + '</span>' +
        (tg.fuego ? '<span class="flame" aria-hidden="true">🔥</span>' : '<span class="bars" aria-hidden="true" data-l="' + l + '"><i></i><i></i><i></i></span>') +
        (mineHere ? '<span class="star" aria-hidden="true">★</span>' : "");
      b.onclick = (function (k) { return function () { select(k); }; })(key);
      strip.appendChild(b);
    }
    var end = new Date(start); end.setDate(end.getDate() + 6);
    $("weekTitle").textContent = state.weekStart === 0 ? T("next7") : T("fromTo", { a: shortDate(start), b: shortDate(end) });
    $("prev").disabled = state.weekStart <= 0;
    $("nextw").disabled = state.weekStart >= 18;
  }

  // ---------- Mapa ----------
  var map, zoneLayer, liveLayer, quietLayer, noiseLayer, liveData = null;
  function initMap() {
    if (!window.L) { $("map").hidden = true; return; }  // sin conexión y sin Leaflet guardado
    var dark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    map = L.map("map", { zoomAnimation: false, fadeAnimation: false, markerZoomAnimation: false, scrollWheelZoom: false, keyboard: false }).setView([39.4699, -0.3700], 13);
    var base = L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/" + (dark ? "dark_all" : "light_all") + "/{z}/{x}/{y}{r}.png?key=" + CARTO_KEY, {
      maxZoom: 19, subdomains: "abcd",
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> © <a href="https://carto.com/attributions">CARTO</a>'
    }).addTo(map);
    // Si CARTO falla, se usa el mapa estándar de OpenStreetMap (no necesita clave)
    var errors = 0;
    base.on("tileerror", function () {
      if (++errors !== 4) return;
      map.removeLayer(base);
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' }).addTo(map);
    });
    zoneLayer = L.layerGroup().addTo(map);
    quietLayer = L.layerGroup().addTo(map);
    noiseLayer = L.layerGroup().addTo(map);
    liveLayer = L.layerGroup().addTo(map);
    map.on("zoomend", function () { if (DATA) renderNoise(); });
    // El mapa está oculto para lectores de pantalla (su contenido está en la lista): que nada dentro reciba el foco
    var unfocus = function () { map.getContainer().querySelectorAll("a, button, [tabindex]").forEach(function (el) { el.setAttribute("tabindex", "-1"); }); };
    unfocus(); map.on("layeradd popupopen", unfocus);
  }
  function renderMap() {
    if (zoneLayer) zoneLayer.clearLayers();
    var evs = eventsOn(state.selected), zl = {}, zev = {};
    evs.forEach(function (e) { (e.zones || []).forEach(function (z) { if (!DATA.zones[z]) return; zl[z] = Math.max(zl[z] || 0, e.level); (zev[z] = zev[z] || []).push(e); }); });
    var bounds = [], city = evs.some(function (e) { return (e.tags || []).indexOf("ciudad") >= 0; });
    // Resumen en texto del mapa para lectores de pantalla
    var names = Object.keys(zl).map(function (z) { return zoneName(z) + " (" + T("levels")[zl[z]].toLowerCase() + ")"; });
    $("mapSummary").textContent = (city ? T("cityLabel").replace("🔥 ", "") + ". " : "") + (names.length ? T("mapSummary", { z: names.join(", ") }) : T("mapSummaryNone"));
    if (state.a11y || !map) return;
    if (city) {
      L.circle([39.4699, -0.3700], { radius: 4200, color: css("--l3"), weight: 4, fillColor: css("--l3"), fillOpacity: 0.22, interactive: false }).addTo(zoneLayer);
      L.tooltip({ permanent: true, direction: "center", className: "citylabel" }).setLatLng([39.4950, -0.3700]).setContent(esc(T("cityLabel"))).addTo(zoneLayer);
    }
    patternsOn(state.selected).forEach(function (p) {
      if (zl[p.zone] || !DATA.zones[p.zone]) return;
      var Z = DATA.zones[p.zone];
      L.circle([Z.lat, Z.lon], { radius: Z.r, color: css("--muted"), weight: 2, dashArray: "6 6", fillOpacity: 0.06 })
        .bindPopup("<strong>" + esc(tx(Z, "name")) + "</strong><br>" + esc(T("usuallyBusy")) + " " + esc(p.from + "–" + p.to) + "<br>" + esc(tx(p, "label"))).addTo(zoneLayer);
    });
    Object.keys(zl).sort(function (a, b) { return zl[a] - zl[b]; }).forEach(function (z) {
      var Z = DATA.zones[z], col = css("--l" + zl[z]);
      var html = "<strong>" + esc(tx(Z, "name")) + "</strong> · " + esc(T("levels")[zl[z]]) + "<br>" + zev[z].map(function (e) { return esc(timeText(e)) + " · " + esc(tx(e, "title")); }).join("<br>");
      L.circle([Z.lat, Z.lon], { radius: Z.r * (zl[z] === 3 ? 1.2 : 1), color: col, weight: 3, fillColor: col, fillOpacity: 0.25 })
        .bindPopup(html).bindTooltip(esc(tx(Z, "name")), { permanent: !city, direction: "top", className: "zl" }).addTo(zoneLayer);
      if (zev[z].some(function (e) { return (e.tags || []).indexOf("fuego") >= 0; })) {
        L.marker([Z.lat, Z.lon], { icon: L.divIcon({ className: "flame-icon", html: "🔥", iconSize: [26, 26] }), keyboard: false }).bindPopup(html).addTo(zoneLayer);
      }
      bounds.push([Z.lat, Z.lon]);
    });
    evs.forEach(function (e) {
      if ((e.zones || []).length || !(e.geo || []).length) return;
      var col = css("--l" + e.level);
      e.geo.forEach(function (pt) {
        L.circle(pt, { radius: 90, color: col, weight: 2, fillColor: col, fillOpacity: 0.35 }).bindPopup("<strong>" + esc(tx(e, "title")) + "</strong><br>" + esc(timeText(e))).addTo(zoneLayer);
        bounds.push(pt);
      });
    });
    if (city) map.setView([39.4699, -0.3700], 12, { animate: false });
    else if (bounds.length === 1) map.setView(bounds[0], 14, { animate: false });
    else if (bounds.length > 1) map.fitBounds(bounds, { padding: [60, 60], maxZoom: 14, animate: false });
    else map.setView([39.4699, -0.3700], 13, { animate: false });
  }

  // Calles cortadas en tiempo real (Geoportal del Ayuntamiento)
  function estadoOf(props) { for (var k in props) if (/^estado$|estat/i.test(k)) return Number(props[k]); return NaN; }
  function renderLive() {
    if (!map) return;
    liveLayer.clearLayers();
    $("liveNote").hidden = true;
    if (!state.live) return;
    var draw = function () {
      var cut = (liveData.features || []).filter(function (f) { return estadoOf(f.properties || {}) === 3; });
      var streets = cut.map(function (f) { return (f.properties || {}).denominacion; }).filter(Boolean);
      if (!state.a11y) {
        L.geoJSON({ type: "FeatureCollection", features: cut }, { style: { color: css("--l3"), weight: 6, opacity: 0.9 } })
          .bindPopup(function (l) { var p = l.feature.properties || {}; return "<strong>" + esc(T("liveStreet")) + "</strong><br>" + esc(p.denominacion || ""); }).addTo(liveLayer);
      }
      $("liveNote").hidden = false;
      $("liveNote").textContent = cut.length ? T("liveCut", { n: cut.length }) + (streets.length ? " " + streets.slice(0, 12).join(", ") + "." : "") : T("liveNone");
    };
    if (liveData) return draw();
    $("liveNote").hidden = false; $("liveNote").textContent = T("liveLoading");
    fetch(LIVE_URL).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (j) { liveData = j; draw(); })
      .catch(function () { $("liveNote").textContent = T("liveError"); state.live = false; $("live").checked = false; });
  }

  // ---------- Detalle del día ----------
  // Avisos de AEMET que tocan ese día, con la franja horaria de ese día
  function weatherOn(day) {
    return ((DATA && DATA.weather) || []).map(function (w) {
      var a = w.from.slice(0, 10), b = w.to.slice(0, 10), endT = w.to.slice(11, 16);
      if (endT === "00:00") { var d = parse(b); d.setDate(d.getDate() - 1); b = ymd(d); endT = "24:00"; }
      if (day < a || day > b) return null;
      var f = day === a ? w.from.slice(11, 16) : "00:00", t = day === b ? endT : "24:00";
      return { kind: w.kind, level: w.level, url: w.url, span: (f === "00:00" && (t === "24:00" || t === "23:59")) ? T("allDay") : f + "–" + (t === "24:00" ? "23:59" : t) };
    }).filter(Boolean).sort(function (x, y) { return y.level - x.level; });
  }
  function renderDay() {
    var title = (state.selected === TODAY ? T("todayComma", { d: longDate(parse(state.selected)) }) : longDate(parse(state.selected)));
    $("dayTitle").textContent = cap(title);
    var evs = eventsOn(state.selected).slice().sort(function (a, b) { return (isMine(b) ? 1 : 0) - (isMine(a) ? 1 : 0); }), pats = patternsOn(state.selected), h = "";
    if (!evs.length) h += '<p class="empty">' + esc(T("noEvents")) + "</p>";
    if (tagsOn(state.selected).ciudad) h += '<p class="citywide">' + esc(T("fallasBanner")) + "</p>";
    weatherOn(state.selected).forEach(function (w) {
      var pk = { thunderstorm: "tormenta", rain: "lluvia", "high-temperature": "calor", wind: "viento" }[w.kind] || "lluvia";
      h += '<div class="weather w' + w.level + '">' + picto(pk, "small") + "<p><strong>" + esc(T("weatherWarn", { c: T("wColors")[w.level], k: (T("wKinds")[w.kind] || T("wKinds").other) })) + "</strong><br>" +
        esc(w.span) + (w.kind === "thunderstorm" ? " " + esc(T("weatherStorm")) : "") + ' <a href="' + esc(w.url) + '" target="_blank" rel="noopener">AEMET</a></p></div>';
    });
    evs.forEach(function (e) {
      var links = srcLink(e.source.name, e.source.url, T("source"));
      (e.also || []).forEach(function (s) { links += srcLink(s.name, s.url, T("alsoIn")); });
      var fire = (e.tags || []).indexOf("fuego") >= 0;
      h += '<article class="ev" data-l="' + e.level + '"><div class="evhead">' + picto(pictoKey(e)) + '<div><h3>' + esc(tx(e, "title")) + "</h3>" +
        '<div class="row">' + (isMine(e) && !isCityWide(e) ? '<span class="pill mine-pill">' + esc(T("minePill")) + "</span>" : "") + '<span class="pill l' + e.level + '">' + esc(T("levels")[e.level]) + "</span>" +
        (fire ? '<span class="pill fire">' + esc(T("pillFire")) + "</span>" : "") +
        (e.official ? '<span class="pill off">' + esc(T("official")) + "</span>" : "") +
        (e.confirmed === false ? '<span class="pill warn">' + esc(T("unconfirmed")) + "</span>" : "") +
        '<span class="sub people">' + esc(typeName(e.type)) + (tx(e, "people") ? " · " + esc(tx(e, "people")) : "") + "</span></div></div></div>" +
        '<div class="row"><span class="when">' + esc(timeText(e)) + "</span>" + (e.start && e.from && e.start !== e.from ? '<span class="sub">' + esc(T("startsAt", { t: e.start })) + "</span>" : "") + "</div>" +
        '<p class="avoid"><strong>' + esc(T("avoidZone")) + "</strong> " + esc(zoneNames(e)) + (tx(e, "tip") ? '<span class="tip"><br>' + esc(tx(e, "tip")) + "</span>" : "") + "</p>" +
        (fire ? '<div class="evhead">' + picto("cascos", "small") + '<p class="sub">' + esc(T("earsTip")) + "</p></div>" : "") +
        (e.raw ? '<details class="raw"><summary>' + esc(T("rawSummary")) + "</summary><p>" + esc(e.raw) + "</p></details>" : "") +
        '<div class="links">' + links + "</div></article>";
    });
    if (pats.length) {
      h += '<h3 class="habtitle">' + esc(T("habitualTitle")) + "</h3>";
      pats.forEach(function (p) {
        h += '<article class="ev pattern"><div class="row"><span class="pill warn">' + esc(T("habitual")) + '</span><span class="when">' + esc(p.from + "–" + p.to) + "</span></div><p>" + esc(tx(p, "label")) + "</p></article>";
      });
    }
    $("events").innerHTML = h;
  }

  function renderFooter() {
    var n = DATA.notices || [];
    $("noticesCard").hidden = !n.length;
    $("notices").innerHTML = n.map(function (x) {
      return '<li><a href="' + esc(x.url) + '" target="_blank" rel="noopener">' + esc(x.title) + '</a> <span class="sub">(' + esc(x.date.split("-").reverse().join("/")) + ")</span></li>";
    }).join("");
    $("sources").innerHTML = (DATA.sources || []).map(function (s) {
      return "<li>" + esc(s.name) + (s.ok ? "" : ' <span class="bad">' + esc(T("sourceDown")) + "</span>") + "</li>";
    }).join("") + "<li>" + esc(T("liveSource")) + "</li>";
    var u = new Date(DATA.updated);
    $("updated").textContent = T("updated", { d: shortDate(u), t: String(u.getHours()).padStart(2, "0") + ":" + String(u.getMinutes()).padStart(2, "0") });
  }

  // ---------- Lugares y horas tranquilas ----------
  function dist(a, b, c, d) { var dx = (b - d) * 85000, dy = (a - c) * 111000; return Math.sqrt(dx * dx + dy * dy); }
  function nearbyEvent(pl, date) {
    return eventsOn(date).filter(function (e) {
      return (e.tags || []).indexOf("ciudad") >= 0 || (e.zones || []).some(function (z) { var Z = DATA.zones[z]; return Z && dist(pl.lat, pl.lon, Z.lat, Z.lon) < Z.r + 400; });
    })[0];
  }
  function nowIn(from, to) {
    var n = new Date(), m = n.getHours() * 60 + n.getMinutes(), f = from.split(":"), t = to.split(":");
    return m >= +f[0] * 60 + +f[1] && m < +t[0] * 60 + +t[1];
  }
  function quietHoursOn(date) { var wd = parse(date).getDay(); return QUIET.hours.filter(function (q) { return q.days.indexOf(wd) >= 0; }); }
  function renderQuiet() {
    var isToday = state.selected === TODAY;
    $("quietHours").innerHTML = quietHoursOn(state.selected).map(function (q) {
      var live = isToday && nowIn(q.from, q.to);
      return '<article class="ev quiet"><div class="evhead">' + picto(q.picto) + '<div><h3>' + esc(tx(q, "title")) + '</h3><div class="row">' +
        (live ? '<span class="pill now">' + esc(T("nowLive")) + "</span>" : '<span class="pill calm">' + esc(T("quietHour")) + "</span>") +
        '<span class="when">' + esc(tx(q, "when")) + "</span></div></div></div><p>" + esc(tx(q, "text")) +
        '</p><div class="links">' + srcLink(q.source.name, q.source.url, T("source")) + "</div></article>";
    }).join("");
    $("quietPlaces").innerHTML = QUIET.places.map(function (pl) {
      var ev = nearbyEvent(pl, state.selected);
      return '<article class="ev quiet' + (ev ? " warn" : "") + '"><div class="evhead">' + picto(pl.picto) + '<div><h3>' + esc(tx(pl, "name")) + '</h3><div class="row">' +
        (ev ? '<span class="pill l2">' + esc(T("notCalm")) + "</span>" : '<span class="pill calm">' + esc(T("quietPlace")) + "</span>") +
        '<span class="sub">' + esc(tx(pl, "best")) + "</span></div></div></div>" +
        (ev ? '<p class="avoid">' + esc(T("nearby")) + " <strong>" + esc(tx(ev, "title")) + "</strong> (" + esc(timeText(ev)) + ").</p>" : "") +
        "<p>" + esc(tx(pl, "text")) + '</p><div class="links">' + srcLink(pl.source.name, pl.source.url, T("source")) + "</div></article>";
    }).join("");
    var refs = (DATA && DATA.refuges) || [];
    $("refugesBox").hidden = !refs.length;
    $("refugesTitle").textContent = T("refugesTitle", { n: refs.length });
    $("refugesList").innerHTML = refs.map(function (r) {
      var ev = nearbyEvent(r, state.selected);
      return "<li>" + picto(r.kind === "biblioteca" ? "biblioteca" : "museo", "small") + "<span><strong>" + esc(r.name) + "</strong><br>" +
        '<span class="sub">' + esc(T("refugeKinds")[r.kind] || "") + (ev ? " · " + esc(T("eventNear", { t: tx(ev, "title") })) : "") + "</span> " +
        '<a href="https://www.google.com/maps/search/?api=1&query=' + r.lat + "," + r.lon + '" target="_blank" rel="noopener">' + esc(T("howToGet")) + "</a></span></li>";
    }).join("");
  }
  function renderQuietMap() {
    if (!map) return;
    quietLayer.clearLayers();
    if (!state.quiet || state.a11y) return;
    QUIET.places.forEach(function (pl) {
      var ev = nearbyEvent(pl, state.selected);
      L.marker([pl.lat, pl.lon], { icon: L.divIcon({ className: "quiet-icon", html: '<img src="pictos/' + pl.picto + '.png" alt="">', iconSize: [34, 34] }), keyboard: false, opacity: ev ? 0.5 : 1 })
        .bindPopup("<strong>" + esc(tx(pl, "name")) + "</strong><br>" + (ev ? esc(T("eventNear", { t: tx(ev, "title") })) : esc(tx(pl, "best")))).addTo(quietLayer);
    });
    ((DATA && DATA.refuges) || []).forEach(function (r) {
      var ev = nearbyEvent(r, state.selected);
      L.marker([r.lat, r.lon], { icon: L.divIcon({ className: "quiet-icon small", html: '<img src="pictos/' + (r.kind === "biblioteca" ? "biblioteca" : "museo") + '.png" alt="">', iconSize: [26, 26] }), keyboard: false, opacity: ev ? 0.5 : 0.9 })
        .bindPopup("<strong>" + esc(r.name) + "</strong><br>" + esc(T("refugeKinds")[r.kind] || "") + (ev ? "<br>" + esc(T("eventNear", { t: tx(ev, "title") })) : "")).addTo(quietLayer);
    });
  }

  // ---------- Ruido ----------
  function dbColor(v) { return v == null ? css("--muted") : v < 55 ? css("--calm") : v < 60 ? css("--l1") : v < 65 ? css("--l2") : css("--l3"); }
  function noisePeriod() {
    var hour = new Date().getHours();
    return hour >= 23 || hour < 7 ? ["laeq_n", T("noiseNight")] : hour >= 19 ? ["laeq_e", T("noiseEve")] : ["laeq_d", T("noiseDay")];
  }
  function renderNoise() {
    if (!map) return;
    noiseLayer.clearLayers();
    var note = $("noiseNote"), data = DATA.noise || [];
    if (!state.noise || !data.length) { note.hidden = true; return; }
    var per = noisePeriod(), field = per[0], label = per[1];
    var vals = data.map(function (n) { return n[field] != null ? n[field] : n.laeq; }).filter(function (v) { return v != null; });
    var avg = vals.length ? vals.reduce(function (a, b) { return a + b; }, 0) / vals.length : null, mx = vals.length ? Math.max.apply(null, vals) : null;
    if (!state.a11y) {
      if (map.getZoom() < 16 && vals.length) {
        var la = data.reduce(function (a, n) { return a + n.lat; }, 0) / data.length, lo = data.reduce(function (a, n) { return a + n.lon; }, 0) / data.length;
        L.marker([la, lo], { icon: L.divIcon({ className: "db-icon", html: '<span style="background:' + dbColor(avg) + '">Ruzafa ' + Math.round(avg) + " dB</span>", iconSize: [96, 22], iconAnchor: [48, 11] }), keyboard: false })
          .bindPopup("<strong>" + esc(T("noiseTitle")) + "</strong><br>" + esc(T("noiseAvg", { a: Math.round(avg), m: Math.round(mx), n: vals.length, p: label })) + "<br>" + esc(T("zoomIn"))).addTo(noiseLayer);
      } else data.forEach(function (n) {
        var v = n[field] != null ? n[field] : n.laeq;
        L.marker([n.lat, n.lon], { icon: L.divIcon({ className: "db-icon", html: '<span style="background:' + dbColor(v) + '">' + (v != null ? Math.round(v) + " dB" : "—") + "</span>", iconSize: [48, 22] }), keyboard: false })
          .bindPopup("<strong>" + esc(n.name) + "</strong><br>" + esc(T("noiseMeasured", { d: n.date.split("-").reverse().join("/") })) + "<br>" +
            esc(T("dayEveNight", { a: n.laeq_d == null ? "—" : n.laeq_d, b: n.laeq_e == null ? "—" : n.laeq_e, c: n.laeq_n == null ? "—" : n.laeq_n })) +
            '<br><a href="' + esc(n.source) + '" target="_blank" rel="noopener">' + esc(T("councilData")) + "</a>").addTo(noiseLayer);
      });
    }
    note.hidden = false;
    note.innerHTML = esc(T("noiseNote", { p: label })) + (avg != null ? " <strong>" + esc(T("noiseAvg", { a: Math.round(avg), m: Math.round(mx), n: vals.length, p: label })) + "</strong>" : "") +
      ' <span><b style="background:' + css("--calm") + '"></b>' + esc(T("noiseLow")) + '</span><span><b style="background:' + css("--l1") + '"></b>55–60</span><span><b style="background:' + css("--l2") +
      '"></b>60–65</span><span><b style="background:' + css("--l3") + '"></b>' + esc(T("noiseHigh")) + "</span>";
  }

  // ---------- Modo accesible y lectura en voz alta ----------
  function applyA11y() {
    document.body.classList.toggle("a11y", state.a11y);
    document.body.classList.toggle("dys", state.dys);
    document.body.classList.toggle("simple", state.simple);
    document.documentElement.classList.remove("sz2", "sz3");
    if (state.size > 1) document.documentElement.classList.add("sz" + state.size);
    $("optBlind").checked = state.a11y; $("optDys").checked = state.dys; $("optSimple").checked = state.simple;
    $("sz" + state.size).checked = true;
    $("map").hidden = state.a11y;
    $("mapHidden").hidden = !state.a11y;
    document.querySelectorAll(".mapopt").forEach(function (el) { el.hidden = state.a11y && el.id !== "liveLabel"; });
    if (!state.a11y && map && DATA) setTimeout(function () { map.invalidateSize(); renderMap(); renderQuietMap(); renderNoise(); renderLive(); }, 0);
  }
  var speaking = false;
  function speechText() {
    var d = parse(state.selected), parts = [];
    if (state.selected === TODAY) parts.push($("statusTitle").textContent.replace("🔥", "") + ".");
    if (state.selected === TODAY && !$("mineBox").hidden) parts.push($("mineBox").innerText.replace(/★/g, "").replace(/\n/g, ". ") + ".");
    parts.push(cap(longDate(d)) + ".");
    var evs = eventsOn(state.selected);
    if (!evs.length) parts.push(T("speechNoEvents"));
    if (tagsOn(state.selected).ciudad) parts.push(T("fallasBanner").replace("🔥", ""));
    evs.forEach(function (e) {
      parts.push(T("speechEvent", { l: T("levels")[e.level], t: tx(e, "title"), w: timeText(e).replace("–", " - "), z: zoneNames(e) }) + " " + tx(e, "tip"));
    });
    var calm = QUIET.places.filter(function (pl) { return !nearbyEvent(pl, state.selected); }).map(function (pl) { return tx(pl, "name"); });
    if (calm.length) parts.push(T("speechQuiet", { p: calm.join(", ") }));
    return parts.join(" ").replace(/→/g, ",").replace(/\s+/g, " ");
  }
  function stopSpeech() { if (window.speechSynthesis) window.speechSynthesis.cancel(); speaking = false; $("speakBtn").textContent = T("listen"); }
  function speak() {
    if (!("speechSynthesis" in window)) { $("speakNote").textContent = T("noVoice"); return; }
    if (speaking) return stopSpeech();
    var u = new SpeechSynthesisUtterance(speechText());
    u.lang = T("speechLang");
    var voices = window.speechSynthesis.getVoices(), base = u.lang.slice(0, 2);
    var v = voices.filter(function (x) { return x.lang && x.lang.replace("_", "-").indexOf(u.lang) === 0; })[0] || voices.filter(function (x) { return x.lang && x.lang.indexOf(base) === 0; })[0];
    if (v) u.voice = v;
    u.rate = 0.95;
    u.onend = u.onerror = function () { speaking = false; $("speakBtn").textContent = T("listen"); };
    speaking = true; $("speakBtn").textContent = T("stop");
    window.speechSynthesis.speak(u);
  }

  function select(date) {
    stopSpeech();
    state.selected = date;
    var diff = Math.round((parse(date) - today) / 86400000);
    if (diff >= 0) state.weekStart = Math.floor(diff / 7);
    renderAll();
  }
  function renderAll() { renderStatus(); renderStrip(); renderMap(); renderDay(); renderQuiet(); renderQuietMap(); }
  function setLang(l) {
    if (!I18N[l]) return;
    stopSpeech();
    LANG = l; store.set("vsa-lang", l);
    applyStatic();
    if (DATA) { renderAll(); renderFooter(); renderNoise(); if (state.live) renderLive(); if (!$("sitesPanel").hidden) renderAreas(); renderOffline(); }
  }

  // ---------- Controles ----------
  $("sens").checked = state.minLevel === 1;
  $("pat").checked = state.patterns;
  $("live").checked = state.live;
  $("quietChk").checked = state.quiet;
  $("noiseChk").checked = state.noise;
  $("quietChk").onchange = function (ev) { state.quiet = ev.target.checked; store.set("vsa-quiet", state.quiet); renderQuietMap(); };
  $("noiseChk").onchange = function (ev) { state.noise = ev.target.checked; store.set("vsa-noise", state.noise); renderNoise(); };
  $("sens").onchange = function (ev) { state.minLevel = ev.target.checked ? 1 : 2; store.set("vsa-small", ev.target.checked); renderAll(); };
  $("pat").onchange = function (ev) { state.patterns = ev.target.checked; store.set("vsa-patterns", ev.target.checked); renderMap(); renderDay(); };
  $("live").onchange = function (ev) { state.live = ev.target.checked; store.set("vsa-live", ev.target.checked); renderLive(); };
  $("prev").onclick = function () { if (state.weekStart > 0) { state.weekStart--; renderStrip(); } };
  $("nextw").onclick = function () { if (state.weekStart < 18) { state.weekStart++; renderStrip(); } };
  $("copyTopic").onclick = function () {
    var t = $("topic").textContent;
    if (navigator.clipboard) navigator.clipboard.writeText(t).then(function () { $("copyTopic").textContent = T("copied"); }, function () {});
  };
  document.querySelectorAll(".lang").forEach(function (b) { b.onclick = function () { setLang(b.dataset.lang); }; });
  function renderAreas() {
    $("areasList").innerHTML = Object.keys(AREAS).map(function (a) {
      var places = AREAS[a].filter(function (z) { return DATA && DATA.zones[z]; }).map(zoneName).join(", ");
      var topic = $("topic").textContent.trim() + "-" + a, on = state.mine.indexOf(a) >= 0;
      return '<div class="area"><label class="opt" for="ar_' + a + '"><input type="checkbox" id="ar_' + a + '" value="' + a + '"' + (on ? " checked" : "") + "> <span><strong>" +
        esc(T("areas")[a]) + "</strong>" + (places ? '<br><span class="sub">' + esc(places) + "</span>" : "") + "</span></label>" +
        (on ? '<div class="sub2"><a class="link small subbtn" href="https://ntfy.sh/' + esc(topic) + '" target="_blank" rel="noopener">' + esc(T("subscribe")) + '</a> <a class="link small subbtn" href="' + esc(calUrl(a, APPLE ? "webcal" : "google")) + '" target="_blank" rel="noopener">' + esc(T("calArea")) + '</a> <span class="sub">' + esc(T("channel")) + " <code>" + esc(topic) + "</code></span></div>" : "") + "</div>";
    }).join("") + (state.mine.length ? '<p class="sub">' + esc(T("subHelp")) + "</p>" : "");
    $("areasList").querySelectorAll("input").forEach(function (inp) {
      inp.onchange = function () {
        state.mine = Array.prototype.map.call($("areasList").querySelectorAll("input:checked"), function (x) { return x.value; });
        store.set("vsa-mine", state.mine);
        var id = inp.id;
        renderAll(); renderAreas();
        var again = $(id); if (again) again.focus();
      };
    });
    $("onlyMine").checked = state.onlyMine;
  }
  $("onlyMine").onchange = function (ev) { state.onlyMine = ev.target.checked; store.set("vsa-onlymine", state.onlyMine); renderAll(); };
  function togglePanel(btn, panel, other, otherBtn) {
    var open = $(panel).hidden;
    $(panel).hidden = !open; $(btn).setAttribute("aria-expanded", open ? "true" : "false");
    if (open) { $(other).hidden = true; $(otherBtn).setAttribute("aria-expanded", "false"); var f = $(panel).querySelector("input"); if (f) f.focus(); }
  }
  $("sitesBtn").onclick = function () { renderAreas(); togglePanel("sitesBtn", "sitesPanel", "a11yPanel", "panelBtn"); };
  $("panelBtn").onclick = function () { togglePanel("panelBtn", "a11yPanel", "sitesPanel", "sitesBtn"); };
  $("optBlind").onchange = function (ev) { state.a11y = ev.target.checked; store.set("vsa-a11y", state.a11y); applyA11y(); renderAll(); renderNoise(); renderLive(); };
  $("optDys").onchange = function (ev) { state.dys = ev.target.checked; store.set("vsa-dys", state.dys); applyA11y(); if (map) setTimeout(function () { map.invalidateSize(); }, 50); };
  $("optSimple").onchange = function (ev) { state.simple = ev.target.checked; store.set("vsa-simple", state.simple); applyA11y(); };
  document.querySelectorAll('input[name="sz"]').forEach(function (r) {
    r.onchange = function () { state.size = +r.value; store.set("vsa-size", state.size); applyA11y(); if (map) setTimeout(function () { map.invalidateSize(); }, 50); };
  });
  $("speakBtn").onclick = speak;
  if (window.speechSynthesis) window.speechSynthesis.onvoiceschanged = function () {};
  $("dayTitle").setAttribute("tabindex", "-1");

  // ---------- Calendario (.ics) ----------
  var APPLE = /iPhone|iPad|Macintosh/.test(navigator.userAgent);
  function calUrl(area, kind) {
    var u = new URL("cal/" + (area || "valencia") + ".ics", location.href).href, wc = u.replace(/^https?:/, "webcal:");
    if (kind === "google") return "https://calendar.google.com/calendar/render?cid=" + encodeURIComponent(wc);
    if (kind === "webcal") return wc;
    return u;
  }
  $("calGoogle").href = calUrl("", "google");
  $("calApple").href = calUrl("", "webcal");
  $("calCopy").onclick = function () {
    if (navigator.clipboard) navigator.clipboard.writeText(calUrl("")).then(function () { $("calCopy").textContent = T("copied"); }, function () {});
  };

  // ---------- Instalar como app / sin conexión ----------
  var installEvt = null;
  window.addEventListener("beforeinstallprompt", function (ev) { ev.preventDefault(); installEvt = ev; $("installBtn").hidden = false; });
  $("installBtn").onclick = function () {
    if (!installEvt) return;
    installEvt.prompt();
    installEvt.userChoice.then(function () { installEvt = null; $("installBtn").hidden = true; });
  };
  var standalone = (window.matchMedia && window.matchMedia("(display-mode: standalone)").matches) || navigator.standalone;
  if (standalone) $("installCard").hidden = true;
  function renderOffline() {
    var b = $("offlineBar");
    if (navigator.onLine || !DATA) { b.hidden = true; return; }
    var u = new Date(DATA.updated);
    b.textContent = T("offline", { d: shortDate(u) + " " + String(u.getHours()).padStart(2, "0") + ":" + String(u.getMinutes()).padStart(2, "0") });
    b.hidden = false;
  }
  window.addEventListener("online", renderOffline);
  window.addEventListener("offline", renderOffline);
  if ("serviceWorker" in navigator && location.protocol !== "file:") {
    window.addEventListener("load", function () { navigator.serviceWorker.register("sw.js").catch(function () {}); });
  }

  // ---------- Contacto ----------
  function contactEmail() { return CONTACT.user && CONTACT.domain ? CONTACT.user + "@" + CONTACT.domain : ""; }
  if (contactEmail()) {
    $("contact").hidden = false;
    $("cEmail").textContent = contactEmail();
    $("cCopy").onclick = function () {
      if (navigator.clipboard) navigator.clipboard.writeText(contactEmail()).then(function () { $("cCopy").textContent = T("copied"); }, function () {});
    };
    $("contactForm").onsubmit = function (ev) {
      ev.preventDefault();
      var msg = $("cMsg").value.trim(), err = $("cError");
      if (!msg) { err.textContent = T("cEmpty"); err.hidden = false; $("cMsg").setAttribute("aria-invalid", "true"); $("cMsg").focus(); return; }
      err.hidden = true; $("cMsg").removeAttribute("aria-invalid");
      var sel = $("cReason"), reason = sel.options[sel.selectedIndex].textContent, name = $("cName").value.trim();
      var body = msg + "\n\n" + (name ? T("cFrom", { n: name }) + "\n" : "") + "— " + location.href.split("#")[0] + " (" + LANG + ")";
      location.href = "mailto:" + contactEmail() + "?subject=" + encodeURIComponent(T("cSubject", { r: reason })) + "&body=" + encodeURIComponent(body);
      $("cDone").textContent = T("cOpened");
    };
  }

  if (BMC_USER) { $("coffeeLink").href = "https://www.buymeacoffee.com/" + encodeURIComponent(BMC_USER); $("support").hidden = false; }
  applyStatic();
  initMap();
  applyA11y();
  fetch("data/events.json", { cache: "no-store" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (j) {
      DATA = j;
      if (DATA.areas) AREAS = DATA.areas;
      return fetch("data/quiet.json", { cache: "no-store" }).then(function (r) { return r.ok ? r.json() : { hours: [], places: [] }; })
        .catch(function () { return { hours: [], places: [] }; })
        .then(function (q) { QUIET = q; renderAll(); renderFooter(); renderLive(); renderNoise(); renderOffline(); });
    })
    .catch(function () {
      $("statusDate").textContent = "";
      $("statusTitle").textContent = T("errorTitle");
      $("statusText").textContent = T("errorText");
    });
})();
