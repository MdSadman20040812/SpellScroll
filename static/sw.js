/* SpellScroll service worker.
 *
 * Strategy by request type:
 *   - navigations: network first, cached shell as the offline fallback
 *   - static assets and covers: stale-while-revalidate (covers are
 *     content-addressed by upstream URL, so a cached one is never wrong)
 *   - API and WebSocket traffic: never cached
 *
 * The previous version pre-cached a list of third-party CDN URLs (Tailwind,
 * Alpine, FontAwesome). `cache.addAll` rejects if *any* entry fails, so once
 * those CDNs were dropped from the app the install step failed permanently and
 * a stale worker kept serving old HTML. Only same-origin assets that are known
 * to exist are pre-cached now, and each is added individually so one failure
 * cannot poison the install.
 */
const VERSION = 'v3';
const SHELL_CACHE = `spellscroll-shell-${VERSION}`;
const ASSET_CACHE = `spellscroll-assets-${VERSION}`;
const OFFLINE_URL = '/offline/';

const SHELL_ASSETS = [
  OFFLINE_URL,
  '/static/css/tokens.css',
  '/static/css/spellscroll.css',
  '/static/js/app.js',
  '/static/manifest.json',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) =>
      Promise.all(
        SHELL_ASSETS.map((url) =>
          cache.add(url).catch(() => {
            /* a missing asset must not abort the whole install */
          })
        )
      )
    ).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key !== SHELL_CACHE && key !== ASSET_CACHE)
            .map((key) => caches.delete(key))
        )
      )
      .then(() => self.clients.claim())
  );
});

/** Let the page trigger an immediate update after a deploy. */
self.addEventListener('message', (event) => {
  if (event.data === 'skip-waiting') {
    self.skipWaiting();
  }
});

function isCacheableAsset(url) {
  return (
    url.pathname.startsWith('/static/') ||
    url.pathname.startsWith('/cover/') ||
    url.pathname.startsWith('/media/')
  );
}

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') {
    return;
  }

  const url = new URL(request.url);

  // Live data and sockets always go to the network.
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/ws/')) {
    return;
  }

  // Cross-origin (fonts) is left to the browser's own HTTP cache.
  if (url.origin !== self.location.origin) {
    return;
  }

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches.open(SHELL_CACHE).then((cache) => cache.put(request, copy));
          return response;
        })
        .catch(() =>
          caches
            .match(request)
            .then((cached) => cached || caches.match(OFFLINE_URL))
        )
    );
    return;
  }

  if (!isCacheableAsset(url)) {
    return;
  }

  event.respondWith(
    caches.open(ASSET_CACHE).then((cache) =>
      cache.match(request).then((cached) => {
        const network = fetch(request)
          .then((response) => {
            if (response && response.status === 200) {
              cache.put(request, response.clone());
            }
            return response;
          })
          .catch(() => cached);
        return cached || network;
      })
    )
  );
});
