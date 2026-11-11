// Service worker minimal : le site reste toujours à jour (réseau d'abord) ;
// les fichiers du site déjà visités sont gardés en secours si la connexion tombe.
const CACHE = 'chesnoy-v1';
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(cles => Promise.all(cles.filter(c => c !== CACHE).map(c => caches.delete(c)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET' || new URL(e.request.url).origin !== self.location.origin) return;
  e.respondWith(
    fetch(e.request).then(r => {
      if (r.ok) { const copie = r.clone(); caches.open(CACHE).then(c => c.put(e.request, copie)); }
      return r;
    }).catch(() => caches.match(e.request))
  );
});
