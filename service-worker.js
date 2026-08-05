/* Haunted Trail Time Clock — service worker
 *
 * Strategy, and why:
 *   HTML  -> network first. The app is updated by replacing index.html, so a
 *            stale cached page is the one failure we cannot tolerate. The cache
 *            is only used when the network genuinely fails.
 *   Assets-> cache first. Icons and CDN libraries never change without a new
 *            filename, so serving them from cache makes cold starts fast.
 *   API   -> never touched. Supabase requests must fail honestly when offline
 *            rather than return stale punches.
 */

// Bumping this name drops every previously cached file on the next visit.
const CACHE = 'timeclock-v2';

const SHELL = [
  '/',
  '/index.html',
  '/manifest.json',
  '/icon-192.png',
  '/icon-512.png',
  '/icon-maskable-512.png'
];

self.addEventListener('install', e => {
  // addAll fails the whole install if any one item 404s, so add them individually.
  e.waitUntil(
    caches.open(CACHE)
      .then(c => Promise.all(SHELL.map(u => c.add(u).catch(() => null))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);

  // Let the database talk to the network on its own terms.
  if (url.hostname.endsWith('supabase.co')) return;

  // Page loads: always try the network first so a new upload lands immediately.
  if (req.mode === 'navigate') {
    e.respondWith(
      fetch(req)
        .then(res => {
          const copy = res.clone();
          caches.open(CACHE).then(c => c.put('/index.html', copy));
          return res;
        })
        .catch(() => caches.match('/index.html').then(r => r || caches.match('/')))
    );
    return;
  }

  // Everything else: cache first, refresh in the background.
  e.respondWith(
    caches.match(req).then(hit => {
      const net = fetch(req).then(res => {
        if (res && (res.ok || res.type === 'opaque')) {
          const copy = res.clone();
          caches.open(CACHE).then(c => c.put(req, copy));
        }
        return res;
      }).catch(() => hit);
      return hit || net;
    })
  );
});
