/* Wedivo service worker (feedback 13/11/2026): installable app, offline shell, Web Push.
 *
 * - Navigations: network first, the cached shell when offline (the SPA then shows its own
 *   « hors ligne » states). Never the API: data always comes fresh from the server.
 * - Built assets (/assets/*, hashed names): cache first, they never change.
 * - Push: shows the notification sent by the server; a click opens (or focuses) its page.
 * Registered as /sw.js?dev=1 during development: no caching at all, only push.
 */
const VERSION = 'wedivo-v1'
const SHELL = `${VERSION}-shell`
const ASSETS = `${VERSION}-assets`
const DEV = new URL(self.location.href).searchParams.has('dev')
const PRECACHE = ['/', '/manifest.webmanifest', '/icon-192.png', '/icon-512.png', '/badge-96.png']

self.addEventListener('install', (event) => {
  self.skipWaiting()
  if (!DEV) event.waitUntil(caches.open(SHELL).then((cache) => cache.addAll(PRECACHE)))
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys.filter((key) => DEV || !key.startsWith(VERSION)).map((key) => caches.delete(key)),
        ),
      )
      .then(() => self.clients.claim()),
  )
})

self.addEventListener('fetch', (event) => {
  if (DEV) return
  const request = event.request
  const url = new URL(request.url)
  if (request.method !== 'GET' || url.origin !== self.location.origin) return
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/admin')) return

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone()
          caches.open(SHELL).then((cache) => cache.put('/', copy))
          return response
        })
        .catch(() => caches.match('/')),
    )
    return
  }
  if (url.pathname.startsWith('/assets/')) {
    event.respondWith(
      caches.match(request).then(
        (hit) =>
          hit ||
          fetch(request).then((response) => {
            if (response.ok) {
              const copy = response.clone()
              caches.open(ASSETS).then((cache) => cache.put(request, copy))
            }
            return response
          }),
      ),
    )
  }
})

self.addEventListener('push', (event) => {
  let data = {}
  try {
    data = event.data ? event.data.json() : {}
  } catch {
    data = { title: 'Wedivo', body: event.data ? event.data.text() : '' }
  }
  const title = data.title || 'Wedivo'
  const options = {
    body: data.body || '',
    icon: '/icon-192.png',
    badge: '/badge-96.png',
    tag: data.tag || undefined,
    renotify: Boolean(data.tag),
    timestamp: Date.now(),
    data: { url: data.url || '/', kind: data.kind || '' },
  }
  event.waitUntil(
    Promise.all([
      self.registration.showNotification(title, options),
      // An open app refreshes what changed (alerts, missions, tasks…) right away.
      self.clients
        .matchAll({ type: 'window', includeUncontrolled: true })
        .then((clients) =>
          clients.forEach((client) => client.postMessage({ type: 'push', kind: data.kind || '' })),
        ),
    ]),
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const target = new URL(event.notification.data?.url || '/', self.location.origin).href
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
      for (const client of clients) {
        if (new URL(client.url).origin === self.location.origin) {
          client.focus()
          return client.navigate ? client.navigate(target) : undefined
        }
      }
      return self.clients.openWindow(target)
    }),
  )
})
