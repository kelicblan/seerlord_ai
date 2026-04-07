/* eslint-disable @typescript-eslint/no-explicit-any */
const CACHE_NAME = 'vue-admin-starter-v1';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/offline.html',
];

self.addEventListener('install', (event: any) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  (self as any).skipWaiting();
});

self.addEventListener('activate', (event: any) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    })
  );
  (self as any).clients.claim();
});

self.addEventListener('fetch', (event: any) => {
  const { request } = event;

  if (request.method !== 'GET') {
    return;
  }

  event.respondWith(
    caches.match(request).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }

      return fetch(request)
        .then((response) => {
          if (!response || response.status !== 200 || response.type !== 'basic') {
            return response;
          }

          const responseToCache = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, responseToCache);
          });

          return response;
        })
        .catch(() => {
          if (request.destination === 'document') {
            return caches.match('/offline.html');
          }
          return new Response('Network error', { status: 408 });
        });
    })
  );
});

self.addEventListener('sync', (event: any) => {
  if (event.tag === 'sync-data') {
    event.waitUntil(syncOfflineData());
  }
});

async function syncOfflineData() {
  try {
    const clients = await (self as any).clients.matchAll();
    clients.forEach((client: any) => {
      client.postMessage({ type: 'SYNC_COMPLETE' });
    });
  } catch (error) {
    console.error('Sync failed:', error);
  }
  (self as any).skipWaiting();
}
