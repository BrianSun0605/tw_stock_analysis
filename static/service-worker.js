const CACHE_NAME = "tw-stock-v10";
const SHELL = [
  "/static/css/app.css?v=9",
  "/static/js/app.js?v=7",
  "/static/js/api.js",
  "/static/js/dom.js",
  "/static/js/export.js",
  "/static/js/render.js",
  "/picture/icon/app-icon.svg",
];

self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

function isDynamic(url) {
  return url.pathname === "/" || ["/analyze", "/task/", "/stream/", "/download/", "/shutdown", "/search", "/ping", "/api/"].some(path => url.pathname.startsWith(path));
}

async function networkFirst(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      await cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;
    throw new Error("offline resource unavailable");
  }
}

self.addEventListener("fetch", event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin || isDynamic(url)) return;
  event.respondWith(networkFirst(request));
});
