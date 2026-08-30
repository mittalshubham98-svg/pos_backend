/* Service worker for the Pilani Supply Co. PWA shell (customer app + admin portal).
   Scope is "/" (see the explicit GET /sw.js route in app/main.py — a worker served from
   under /static/ would default to scope "/static/" and never see navigations to "/" or
   "/admin").

   Deliberately narrow: only the static app shell is cached, and only ever with a
   network-first strategy so a fresh deploy is visible immediately; the cache is purely an
   offline/flaky-network fallback. Anything under /api/ is live pricing, inventory and order
   data and must NEVER be served from a cache — those requests are passed straight to the
   network, untouched, in every code path below. */

const CACHE_NAME = "pos-shell-v1";
const SHELL_URLS = [
  "/",
  "/admin",
  "/static/customer.html",
  "/static/admin.html",
  "/static/api.js",
  "/static/customer-manifest.json",
  "/static/admin-manifest.json",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_URLS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((names) => Promise.all(names.filter((n) => n !== CACHE_NAME).map((n) => caches.delete(n))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // Never intercept the API — always hit the network, no cache read or write, so pricing/
  // orders/inventory are never served stale.
  if (url.pathname.startsWith("/api/")) return;

  // Only handle same-origin GET requests for the whitelisted app-shell URLs; everything else
  // (Google Fonts CDN, POST/PATCH/DELETE, PDF downloads, etc.) goes straight to the network.
  if (req.method !== "GET" || url.origin !== self.location.origin) return;
  if (!SHELL_URLS.includes(url.pathname)) return;

  event.respondWith(
    fetch(req)
      .then((res) => {
        const copy = res.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(req, copy));
        return res;
      })
      .catch(() => caches.match(req))
  );
});
