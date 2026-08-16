/* ===== sw.js — Service Worker ===== */

const CACHE_NAME = 'planner-v2';
const ASSETS = [
    './',
    './index.html',
    './css/main.css',
    './css/calendar.css',
    './css/components.css',
    './css/stats.css',
    './js/utils.js',
    './js/db.js',
    './js/notifications.js',
    './js/calendar.js',
    './js/events.js',
    './js/goals.js',
    './js/notes.js',
    './js/search.js',
    './js/stats.js',
    './js/sync.js',
    './js/app.js',
    './manifest.json',
    './icons/icon-192.png',
    './icons/icon-512.png'
];

// Установка — кэшировать все ресурсы
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(ASSETS);
        })
    );
    self.skipWaiting();
});

// Активация — удалить старые кэши
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
            );
        })
    );
    self.clients.claim();
});

// Запросы — сначала кэш, потом сеть
self.addEventListener('fetch', (event) => {
    // Chart.js CDN — кэшировать отдельно
    if (event.request.url.includes('cdn.jsdelivr.net')) {
        event.respondWith(
            caches.open(CACHE_NAME).then(cache =>
                cache.match(event.request).then(response => {
                    if (response) return response;
                    return fetch(event.request).then(networkResponse => {
                        cache.put(event.request, networkResponse.clone());
                        return networkResponse;
                    });
                })
            )
        );
        return;
    }

    event.respondWith(
        caches.match(event.request).then((response) => {
            return response || fetch(event.request).then((networkResponse) => {
                // Кэшировать новые запросы
                if (networkResponse && networkResponse.status === 200) {
                    const responseClone = networkResponse.clone();
                    caches.open(CACHE_NAME).then(cache => {
                        cache.put(event.request, responseClone);
                    });
                }
                return networkResponse;
            });
        }).catch(() => {
            // Офлайн фоллбэк
            if (event.request.mode === 'navigate') {
                return caches.match('./index.html');
            }
        })
    );
});
