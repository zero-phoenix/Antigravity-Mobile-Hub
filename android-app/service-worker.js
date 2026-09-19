// Service Worker para Antigravity Mobile Hub
const CACHE_NAME = 'antigravity-hub-v1';
const ASSETS_TO_CACHE = [
  '/',
  '/manifest.json',
  '/css/app.css',
  '/js/app.js',
  '/js/gemini_engine.js',
  '/js/github_engine.js',
  '/js/bridge_client.js'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE).catch(() => {});
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  // Solo interceptar peticiones GET hacia archivos estáticos, no hacia APIs ni WebSockets
  if (event.request.method === 'GET' && !event.request.url.includes('/api/') && !event.request.url.includes('/ws/')) {
    event.respondWith(
      fetch(event.request).catch(() => caches.match(event.request))
    );
  }
});

// Manejador de Notificaciones Push Nativas desde la PC
self.addEventListener('push', (event) => {
  let data = { title: 'Antigravity Mobile', body: 'Tarea completada en la PC' };
  if (event.data) {
    try { data = event.data.json(); } catch(e) { data.body = event.data.text(); }
  }
  const options = {
    body: data.body,
    icon: '/manifest.json',
    badge: '/manifest.json',
    vibrate: [200, 100, 200],
    data: { url: '/' }
  };
  event.waitUntil(self.registration.showNotification(data.title, options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then((clientList) => {
      if (clientList.length > 0) {
        return clientList[0].focus();
      }
      return clients.openWindow('/');
    })
  );
});
