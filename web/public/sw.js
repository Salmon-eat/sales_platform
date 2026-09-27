/**
 * Service worker for the installed app.
 *
 * Deliberately careful: a classifieds site is mostly fresh data, and a worker that serves yesterday's
 * page from a cache is worse than no worker at all. So:
 *   - files with a hashed name (/_next/static, icons) are served from the cache, they never change;
 *   - everything else goes to the network first, and only falls back to the cache when there is none;
 *   - anything that is not a plain GET is never touched.
 */

const VERSION = "v2";
// local dev: /_next/static names don't change between edits, so caching them would freeze the site
const DEV = ["localhost", "127.0.0.1"].includes(self.location.hostname);
const STATIC = `citobazar-static-${VERSION}`;
const PAGES = `citobazar-pages-${VERSION}`;
const OFFLINE = "/offline.html";

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(STATIC).then((cache) => cache.add(OFFLINE)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((names) =>
        Promise.all(names.filter((name) => !name.endsWith(VERSION)).map((name) => caches.delete(name))),
      )
      .then(() => self.clients.claim()),
  );
});

function isStatic(url) {
  return (
    url.pathname.startsWith("/_next/static/") ||
    url.pathname.startsWith("/media/") ||
    /\.(png|jpg|jpeg|webp|svg|ico|woff2?)$/.test(url.pathname)
  );
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (DEV || request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  // the admin and everything personal must never sit in a cache on a shared phone
  if (url.pathname.startsWith("/admin") || url.pathname.startsWith("/v1/my")) return;

  if (isStatic(url)) {
    event.respondWith(
      caches.match(request).then(
        (hit) =>
          hit ??
          fetch(request).then((response) => {
            const copy = response.clone();
            caches.open(STATIC).then((cache) => cache.put(request, copy));
            return response;
          }),
      ),
    );
    return;
  }

  if (request.mode !== "navigate") return;

  event.respondWith(
    fetch(request)
      .then((response) => {
        const copy = response.clone();
        caches.open(PAGES).then((cache) => cache.put(request, copy));
        return response;
      })
      .catch(() => caches.match(request).then((hit) => hit ?? caches.match(OFFLINE))),
  );
});
