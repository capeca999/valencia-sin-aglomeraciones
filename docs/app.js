(function () {
  "use strict";
  var LEVELS = { 0: "Tranquilo", 1: "Algo de gente", 2: "Mucha gente", 3: "Muchísima gente" };
  var WD = ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"];
  var WD_LONG = ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"];
  var MO = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
  var MO_LONG = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
  // Clave pública de CARTO Basemaps (gratis para uso no comercial). Va en el navegador: es normal que sea visible.
  // Restríngela a tu dominio (capeca999.github.io) en el panel de CARTO.
  var CARTO_KEY = "cb1_5554_1_8fee9a245a93f097e737999e";
  var LIVE_URL = "https://geoportal.valencia.es/server/rest/services/OPENDATA/Trafico/MapServer/192/query?where=1%3D1&outFields=*&outSR=4326&f=geojson";

  var store = {
    get: function (k, d) { try { var v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
    set: function (k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  };
  function $(id) { return document.getElementById(id); }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function ymd(d) { return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0"); }
  function parse(s) { var p = s.split("-").map(Number); return new Date(p[0], p[1] - 1, p[2]); }
  function longDate(d) { return WD_LONG[d.getDay()] + " " + d.getDate() + " de " + MO_LONG[d.getMonth()]; }
  function cap(s) { return s.charAt(0).toUpperCase() + s.slice(1); }
  function css(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }

  var today = new Date(); today.setHours(0, 0, 0, 0);
  var TODAY = ymd(today);
  var DATA = null;
  var state = { minLevel: store.get("vsa-small", false) ? 1 : 2, patterns: store.get("vsa-patterns", true), live: store.get("vsa-live", false), selected: TODAY, weekStart: 0 };

  function eventsOn(date) { return DATA.events.filter(function (e) { return e.date === date && e.level >= state.minLevel; }); }
  function patternsOn(date) {
    if (!state.patterns) return [];
    var wd = parse(date).getDay();
    return DATA.patterns.filter(function (p) { return p.days.indexOf(wd) >= 0; });
  }
  function levelOn(date) { return eventsOn(date).reduce(function (m, e) { return Math.max(m, e.level); }, 0); }
  function timeText(e) {
    if (e.from) return e.from + "–" + e.to + (e.approx ? " (aprox.)" : "");
    if (e.start) return "Desde las " + e.start;
    return "Hora sin anunciar";
  }
  function zoneNames(e) {
    var n = (e.zones || []).filter(function (z) { return DATA.zones[z]; }).map(function (z) { return DATA.zones[z].name; });
    if (n.length) return n.join(", ");
    if (e.type === "Huelga") return "Toda la ciudad (transporte con servicios mínimos)";
    return (e.geo || []).length ? "Marcado en el mapa" : "Ubicación en el texto del aviso";
  }

  // ---------- Estado de hoy ----------
  function renderStatus() {
    var evs = eventsOn(TODAY), lvl = levelOn(TODAY);
    $("status").dataset.level = lvl;
    $("statusDate").textContent = "Hoy, " + longDate(today);
    if (!evs.length) {
      $("statusTitle").textContent = "Hoy está tranquilo";
      $("statusText").textContent = "No hay grandes eventos previstos en Valencia.";
    } else {
      $("statusTitle").textContent = "Hoy: " + LEVELS[lvl].toLowerCase();
      $("statusText").innerHTML = evs.map(function (e) { return "Evita <strong>" + esc(zoneNames(e)) + "</strong> · " + esc(timeText(e)); }).join("<br>");
    }
    var nx = DATA.events.filter(function (e) { return e.date > TODAY && e.level >= state.minLevel; })[0];
    var box = $("next");
    if (nx) {
      box.hidden = false;
      box.innerHTML = '<span class="sub">Próximo aviso</span><strong>' + esc(cap(longDate(parse(nx.date)))) + "</strong><span>" +
        esc(zoneNames(nx)) + " · " + esc(timeText(nx)) + '</span><button class="link" id="goNext">Ver ese día</button>';
      $("goNext").onclick = function () { select(nx.date); };
    } else box.hidden = true;
  }

  // ---------- Calendario ----------
  function renderStrip() {
    var strip = $("strip");
    var start = new Date(today); start.setDate(start.getDate() + state.weekStart * 7);
    strip.innerHTML = "";
    for (var i = 0; i < 7; i++) {
      var d = new Date(start); d.setDate(d.getDate() + i);
      var key = ymd(d), l = levelOn(key);
      var b = document.createElement("button");
      b.className = "day" + (key === TODAY ? " today" : "");
      b.setAttribute("aria-pressed", key === state.selected ? "true" : "false");
      b.setAttribute("aria-label", longDate(d) + ": " + LEVELS[l]);
      b.innerHTML = '<span class="wd">' + (key === TODAY ? "hoy" : WD[d.getDay()]) + '</span><span class="dn">' + d.getDate() +
        '</span><span class="mo">' + MO[d.getMonth()] + '</span><span class="bars" data-l="' + l + '"><i></i><i></i><i></i></span>';
      b.onclick = (function (k) { return function () { select(k); }; })(key);
      strip.appendChild(b);
    }
    var end = new Date(start); end.setDate(end.getDate() + 6);
    $("weekTitle").textContent = state.weekStart === 0 ? "Próximos 7 días" :
      "Del " + start.getDate() + " " + MO[start.getMonth()] + " al " + end.getDate() + " " + MO[end.getMonth()];
    $("prev").disabled = state.weekStart <= 0;
    $("nextw").disabled = state.weekStart >= 18;
  }

  // ---------- Mapa ----------
  var map, zoneLayer, liveLayer, liveData = null;
  function initMap() {
    var dark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    map = L.map("map", { zoomAnimation: false, fadeAnimation: false, markerZoomAnimation: false, scrollWheelZoom: false }).setView([39.4699, -0.3700], 13);
    var base = L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/" + (dark ? "dark_all" : "light_all") + "/{z}/{x}/{y}{r}.png?key=" + CARTO_KEY, {
      maxZoom: 19, subdomains: "abcd",
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> © <a href="https://carto.com/attributions">CARTO</a>'
    }).addTo(map);
    // Si CARTO falla, se usa el mapa estándar de OpenStreetMap (no necesita clave)
    var errors = 0;
    base.on("tileerror", function () {
      if (++errors !== 4) return;
      map.removeLayer(base);
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19, attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
      }).addTo(map);
    });
    zoneLayer = L.layerGroup().addTo(map);
    liveLayer = L.layerGroup().addTo(map);
  }
  function renderMap() {
    zoneLayer.clearLayers();
    var evs = eventsOn(state.selected), zl = {}, zev = {};
    evs.forEach(function (e) { (e.zones || []).forEach(function (z) { if (!DATA.zones[z]) return; zl[z] = Math.max(zl[z] || 0, e.level); (zev[z] = zev[z] || []).push(e); }); });
    var bounds = [];
    patternsOn(state.selected).forEach(function (p) {
      if (zl[p.zone] || !DATA.zones[p.zone]) return;
      var Z = DATA.zones[p.zone];
      L.circle([Z.lat, Z.lon], { radius: Z.r, color: css("--muted"), weight: 2, dashArray: "6 6", fillOpacity: 0.06 })
        .bindPopup("<strong>" + esc(Z.name) + "</strong><br>Suele llenarse " + esc(p.from + "–" + p.to) + "<br>" + esc(p.label)).addTo(zoneLayer);
    });
    Object.keys(zl).sort(function (a, b) { return zl[a] - zl[b]; }).forEach(function (z) {
      var Z = DATA.zones[z], col = css("--l" + zl[z]);
      var html = "<strong>" + esc(Z.name) + "</strong> · " + LEVELS[zl[z]] + "<br>" + zev[z].map(function (e) { return esc(timeText(e)) + " · " + esc(e.title); }).join("<br>");
      L.circle([Z.lat, Z.lon], { radius: Z.r * (zl[z] === 3 ? 1.2 : 1), color: col, weight: 3, fillColor: col, fillOpacity: 0.25 })
        .bindPopup(html).bindTooltip(Z.name, { permanent: true, direction: "top", className: "zl" }).addTo(zoneLayer);
      bounds.push([Z.lat, Z.lon]);
    });
    evs.forEach(function (e) {
      if ((e.zones || []).length || !(e.geo || []).length) return;
      var col = css("--l" + e.level);
      e.geo.forEach(function (pt) {
        L.circle(pt, { radius: 90, color: col, weight: 2, fillColor: col, fillOpacity: 0.35 })
          .bindPopup("<strong>" + esc(e.title) + "</strong><br>" + esc(timeText(e))).addTo(zoneLayer);
        bounds.push(pt);
      });
    });
    if (bounds.length === 1) map.setView(bounds[0], 14, { animate: false });
    else if (bounds.length > 1) map.fitBounds(bounds, { padding: [60, 60], maxZoom: 14, animate: false });
    else map.setView([39.4699, -0.3700], 13, { animate: false });
  }

  // Calles cortadas en tiempo real (Geoportal del Ayuntamiento)
  function estadoOf(props) {
    for (var k in props) if (/^estado$|estat/i.test(k)) return Number(props[k]);
    return NaN;
  }
  function renderLive() {
    liveLayer.clearLayers();
    $("liveNote").hidden = true;
    if (!state.live) return;
    var draw = function () {
      var cut = (liveData.features || []).filter(function (f) { return estadoOf(f.properties || {}) === 3; });
      L.geoJSON({ type: "FeatureCollection", features: cut }, { style: { color: css("--l3"), weight: 6, opacity: 0.9 } })
        .bindPopup(function (l) { var p = l.feature.properties || {}; return "<strong>Calle cortada ahora</strong><br>" + esc(p.denominacion || p.DENOMINACION || p.nombre || ""); })
        .addTo(liveLayer);
      $("liveNote").hidden = false;
      $("liveNote").textContent = cut.length ? "En rojo, " + cut.length + " tramos cortados al tráfico ahora mismo (Geoportal del Ayuntamiento)." : "Ahora mismo no hay tramos cortados al tráfico según el Ayuntamiento.";
    };
    if (liveData) return draw();
    $("liveNote").hidden = false; $("liveNote").textContent = "Cargando el tráfico en tiempo real…";
    fetch(LIVE_URL).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (j) { liveData = j; draw(); })
      .catch(function () {
        $("liveNote").textContent = "No se ha podido cargar el tráfico en tiempo real del Ayuntamiento. Inténtalo más tarde.";
        state.live = false; $("live").checked = false;
      });
  }

  // ---------- Detalle del día ----------
  function renderDay() {
    var title = (state.selected === TODAY ? "Hoy, " : "") + longDate(parse(state.selected));
    $("dayTitle").textContent = cap(title);
    var evs = eventsOn(state.selected), pats = patternsOn(state.selected), h = "";
    if (!evs.length) h += '<p class="empty">No hay eventos grandes previstos este día.</p>';
    evs.forEach(function (e) {
      var links = '<a href="' + esc(e.source.url) + '" target="_blank" rel="noopener">Fuente: ' + esc(e.source.name) + "</a>";
      (e.also || []).forEach(function (s) { links += '<a href="' + esc(s.url) + '" target="_blank" rel="noopener">También en: ' + esc(s.name) + "</a>"; });
      h += '<article class="ev" data-l="' + e.level + '"><div class="row"><span class="pill l' + e.level + '">' + LEVELS[e.level] + "</span>" +
        (e.official ? '<span class="pill off">Fuente oficial</span>' : "") +
        (e.confirmed === false ? '<span class="pill warn">Sin confirmar</span>' : "") +
        '<span class="sub">' + esc(e.type) + (e.people ? " · " + esc(e.people) : "") + "</span></div>" +
        "<h3>" + esc(e.title) + "</h3>" +
        '<div class="row"><span class="when">' + esc(timeText(e)) + "</span>" + (e.start && e.from && e.start !== e.from ? '<span class="sub">Empieza a las ' + esc(e.start) + "</span>" : "") + "</div>" +
        '<p class="avoid"><strong>Zona a evitar:</strong> ' + esc(zoneNames(e)) + (e.tip ? "<br>" + esc(e.tip) : "") + "</p>" +
        (e.raw ? '<details class="raw"><summary>Texto completo del aviso oficial</summary><p>' + esc(e.raw) + "</p></details>" : "") +
        '<div class="links">' + links + "</div></article>";
    });
    if (pats.length) {
      h += '<h3>Zonas que suelen llenarse este día de la semana</h3>';
      pats.forEach(function (p) {
        h += '<article class="ev pattern"><div class="row"><span class="pill warn">Habitual</span><span class="when">' + esc(p.from + "–" + p.to) + "</span></div><p>" + esc(p.label) + "</p></article>";
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
      return "<li>" + esc(s.name) + (s.ok ? "" : ' <span class="bad">(hoy no ha respondido; se usan los datos anteriores)</span>') + "</li>";
    }).join("") + '<li>Geoportal del Ayuntamiento de València (tráfico en tiempo real)</li>';
  }

  function select(date) {
    state.selected = date;
    var diff = Math.round((parse(date) - today) / 86400000);
    if (diff >= 0) state.weekStart = Math.floor(diff / 7);
    renderAll();
  }
  function renderAll() { renderStatus(); renderStrip(); renderMap(); renderDay(); }

  $("sens").checked = state.minLevel === 1;
  $("pat").checked = state.patterns;
  $("live").checked = state.live;
  $("sens").onchange = function (ev) { state.minLevel = ev.target.checked ? 1 : 2; store.set("vsa-small", ev.target.checked); renderAll(); };
  $("pat").onchange = function (ev) { state.patterns = ev.target.checked; store.set("vsa-patterns", ev.target.checked); renderMap(); renderDay(); };
  $("live").onchange = function (ev) { state.live = ev.target.checked; store.set("vsa-live", ev.target.checked); renderLive(); };
  $("prev").onclick = function () { if (state.weekStart > 0) { state.weekStart--; renderStrip(); } };
  $("nextw").onclick = function () { if (state.weekStart < 18) { state.weekStart++; renderStrip(); } };
  $("copyTopic").onclick = function () {
    var t = $("topic").textContent;
    if (navigator.clipboard) navigator.clipboard.writeText(t).then(function () { $("copyTopic").textContent = "Copiado"; }, function () {});
  };

  initMap();
  fetch("data/events.json", { cache: "no-store" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (j) {
      DATA = j;
      var u = new Date(DATA.updated);
      $("updated").textContent = "Actualizado el " + u.getDate() + " de " + MO_LONG[u.getMonth()] + " a las " + String(u.getHours()).padStart(2, "0") + ":" + String(u.getMinutes()).padStart(2, "0") + ".";
      renderAll(); renderFooter(); renderLive();
    })
    .catch(function () {
      $("statusDate").textContent = "";
      $("statusTitle").textContent = "No se han podido cargar los eventos";
      $("statusText").textContent = "Recarga la página en unos segundos.";
    });
})();
