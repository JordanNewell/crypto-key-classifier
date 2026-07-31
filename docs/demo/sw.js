// crypto-key-classifier demo — service worker.
// Path-agnostic: all URLs resolve relative to sw.js location so the same worker
// works at http://127.0.0.1:8000/ (root scope) and
// https://jordannewell.github.io/crypto-key-classifier/ (subpath scope).

const CACHE_NAME = "ckc-demo-v1";

// Same-origin shell assets. Relative URLs resolve against self.location.href.
const SHELL_ASSETS = [
  "./",
  "./index.html",
  "./app.js",
  "./styles.css",
  "./examples.json",
  "./assets/newell-n.svg",
];

// CDN / PyPI origins use network-first to avoid stale-wheel checksum mismatches
// during Pyodide boot. Anything outside this list falls back to SWR.
const NETWORK_FIRST_ORIGINS = new Set([
  "https://cdn.jsdelivr.net",
  "https://pypi.org",
]);

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) =>
      // addAll is atomic — if any fetch fails, the install bails.
      // Shell URLs are same-origin so CORS isn't an issue here.
      cache.addAll(SHELL_ASSETS)
    ).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) return caches.delete(key);
          return undefined;
        })
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);
  const isSameOrigin = url.origin === self.location.origin;
  const isNetworkFirst = NETWORK_FIRST_ORIGINS.has(url.origin);

  if (isNetworkFirst) {
    event.respondWith(networkFirst(req));
    return;
  }
  if (isSameOrigin) {
    event.respondWith(staleWhileRevalidate(req));
    return;
  }
  // Cross-origin GETs we don't manage (e.g. Google Fonts) — pass through.
});

function staleWhileRevalidate(req) {
  return caches.open(CACHE_NAME).then((cache) =>
    cache.match(req).then((cached) => {
      const fetchPromise = fetch(req).then((res) => {
        if (res && res.status === 200 && res.type !== "opaque") {
          cache.put(req, res.clone()).catch(() => {});
        }
        return res;
      }).catch(() => cached);
      return cached || fetchPromise;
    })
  );
}

function networkFirst(req) {
  return caches.open(CACHE_NAME).then((cache) =>
    fetch(req).then((res) => {
      if (res && res.status === 200) {
        cache.put(req, res.clone()).catch(() => {});
      }
      return res;
    }).catch(() => cache.match(req).then((cached) => cached || Response.error()))
  );
}
