/* Tennis Coach service worker: network-first HTML so updates apply on reload. */
const VERSION = 'v29-20261118';
const CACHE = 'tc-' + VERSION;

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  let url;
  try { url = new URL(req.url); } catch (err) { return; }
  if (url.origin !== self.location.origin) return;
  event.respondWith(networkFirst(req));
});

async function networkFirst(req) {
  const cache = await caches.open(CACHE);
  const isDoc = req.mode === 'navigate' || req.destination === 'document';
  try {
    const fresh = await fetch(req, isDoc ? { cache: 'no-store' } : undefined);
    if (fresh && fresh.ok) {
      try { await cache.put(req, fresh.clone()); } catch (err) {}
    }
    return fresh;
  } catch (err) {
    const cached = await cache.match(req);
    if (cached) return cached;
    throw err;
  }
}
