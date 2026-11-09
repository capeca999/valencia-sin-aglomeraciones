// Service worker: guarda la web para que funcione sin conexión.
// Datos y páginas: primero la red (siempre lo más nuevo); si no hay conexión, lo guardado.
// Pictogramas, fuentes, iconos y Leaflet: primero lo guardado (no cambian).
var CACHE = "vsa-v1";
var CORE = ["./", "index.html", "app.js", "i18n.js", "style.css", "data/events.json", "data/quiet.json",
  "logo.svg", "favicon.svg", "icon-192.png", "site.webmanifest",
  "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css", "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"];

self.addEventListener("install", function (ev) {
  ev.waitUntil(caches.open(CACHE).then(function (c) {
    return Promise.all(CORE.map(function (u) { return c.add(new Request(u, { cache: "reload" })).catch(function () {}); }));
  }).then(function () { return self.skipWaiting(); }));
});

self.addEventListener("activate", function (ev) {
  ev.waitUntil(caches.keys().then(function (ks) {
    return Promise.all(ks.filter(function (k) { return k !== CACHE; }).map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});

function keyOf(req) { var u = new URL(req.url); u.search = ""; return u.href; }

self.addEventListener("fetch", function (ev) {
  var req = ev.request, url = new URL(req.url);
  if (req.method !== "GET") return;
  var local = url.origin === self.location.origin;
  var stable = url.hostname === "unpkg.com" || (local && /\/(pictos|fonts)\/|\.(png|svg|woff2?)$/.test(url.pathname));
  if (!local && !stable) return;  // mapas, tráfico en directo, contador: directo a la red
  if (local && /\.ics$/.test(url.pathname)) return;
  if (stable) {
    ev.respondWith(caches.match(keyOf(req)).then(function (hit) {
      return hit || fetch(req).then(function (res) {
        if (res.ok) { var copy = res.clone(); caches.open(CACHE).then(function (c) { c.put(keyOf(req), copy); }); }
        return res;
      });
    }));
    return;
  }
  ev.respondWith(fetch(req).then(function (res) {
    if (res.ok) { var copy = res.clone(); caches.open(CACHE).then(function (c) { c.put(keyOf(req), copy); }); }
    return res;
  }).catch(function () {
    return caches.match(keyOf(req)).then(function (hit) {
      return hit || (req.mode === "navigate" ? caches.match(new URL("index.html", self.location.href).href) : Response.error());
    });
  }));
});
