// Bump this whenever the cache strategy changes so old caches are purged on
// activate (see the `activate` listener).
const CACHE = "community-chat-v2";
// Files cached up-front during install. Keep this minimal: the app shell
// (index.html) is served network-only at runtime, so we only need the icons
// and manifest for offline.
const PRECACHE = ["/manifest.webmanifest", "/icon-192.png", "/icon-512.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(PRECACHE).catch(() => {}))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
      )
  );
  self.clients.claim();
});

// Decide what to do with a fetch. Anything we don't explicitly handle is
// passed straight through to the network (no SW interference).
self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // Never intercept API, WebSocket, or uploads — let the browser handle them.
  if (
    url.pathname.startsWith("/api/") ||
    url.pathname === "/ws" ||
    url.pathname.startsWith("/uploads/")
  ) {
    return;
  }

  // Hashed build assets (e.g. /assets/index-<hash>.js, *.css, fonts). These
  // are content-hashed so a given URL never changes; cache them forever.
  if (url.pathname.startsWith("/assets/")) {
    e.respondWith(
      caches.match(req).then(
        (cached) =>
          cached ||
          fetch(req).then((res) => {
            if (res.ok) {
              const clone = res.clone();
              caches.open(CACHE).then((cache) => cache.put(req, clone));
            }
            return res;
          })
      )
    );
    return;
  }

  // The app shell and every SPA route navigation (/, /members, /families,
  // /room/:id, ...) is served NETWORK-ONLY. We deliberately do NOT cache
  // index.html under a route key: the server returns the shell for every
  // unknown path, and caching that would pin the old hashed bundle and break
  // deploys. Always hitting the network means the user always gets the
  // current index.html (and thus the current JS/CSS).
});
