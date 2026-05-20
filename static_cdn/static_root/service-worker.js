const CACHE_NAME = 'kristo-mfalme-pos-v2';
const urlsToCache = [
    '/tithe/pos/',
    '/tithe/pos/tithe/',
    '/tithe/pos/offering/',
    '/tithe/pos/dashboard/',
    '/static/manifest.json',
    '/static/icons/icon-192x192.png',
    '/static/icons/icon-512x512.png'
];

// Install event - cache resources
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('Opened cache');
                return cache.addAll(urlsToCache);
            })
    );
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', event => {
    event.respondWith(
        caches.match(event.request)
            .then(response => {
                // Cache hit - return response
                if (response) {
                    return response;
                }
                
                // Clone the request
                const fetchRequest = event.request.clone();
                
                return fetch(fetchRequest).then(response => {
                    // Check if valid response
                    if (!response || response.status !== 200 || response.type !== 'basic') {
                        return response;
                    }
                    
                    // Clone the response
                    const responseToCache = response.clone();
                    
                    caches.open(CACHE_NAME)
                        .then(cache => {
                            cache.put(event.request, responseToCache);
                        });
                    
                    return response;
                });
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    const cacheWhitelist = [CACHE_NAME];
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheWhitelist.indexOf(cacheName) === -1) {
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});

// Background sync for offline operations
self.addEventListener('sync', event => {
    if (event.tag === 'sync-offline-operations') {
        event.waitUntil(syncOfflineOperations());
    }
});

// Sync offline operations when back online
function syncOfflineOperations() {
    // Get offline operations from IndexedDB
    return getOfflineOperations().then(operations => {
        if (operations.length === 0) return;
        
        // Send each operation to the server
        return Promise.all(operations.map(op => {
            return fetch('/tithe/api/v1/sync/offline/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${op.token}`
                },
                body: JSON.stringify(op.data)
            }).then(response => {
                if (response.ok) {
                    // Remove synced operation from IndexedDB
                    return removeOfflineOperation(op.id);
                }
            });
        }));
    });
}

// IndexedDB helpers for offline operations
function getOfflineOperations() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('KristoPOS', 1);
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            const db = request.result;
            const transaction = db.transaction(['operations'], 'readonly');
            const store = transaction.objectStore('operations');
            const getAll = store.getAll();
            
            getAll.onsuccess = () => resolve(getAll.result);
            getAll.onerror = () => reject(getAll.error);
        };
        
        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains('operations')) {
                db.createObjectStore('operations', { keyPath: 'id' });
            }
        };
    });
}

function removeOfflineOperation(id) {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('KristoPOS', 1);
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            const db = request.result;
            const transaction = db.transaction(['operations'], 'readwrite');
            const store = transaction.objectStore('operations');
            const deleteRequest = store.delete(id);
            
            deleteRequest.onsuccess = () => resolve();
            deleteRequest.onerror = () => reject(deleteRequest.error);
        };
    });
}
