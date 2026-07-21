/* Golf Challenge — Service Worker (modo offline automático)
   Guarda as telas no navegador: se a internet cair, o telão, o /camera
   e o /form continuam abrindo normalmente (mesmo com F5). As rotas de
   API nunca são cacheadas — quando falham, o app entra em modo offline
   e sincroniza sozinho depois. */
"use strict";
const CACHE = "golf-v1";
const SHELL = ["/", "/camera", "/form", "/index.html", "/camera.html", "/form.html"];

self.addEventListener("install", e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", e => {
  const u = new URL(e.request.url);
  if (u.origin !== location.origin) return;
  if (e.request.method !== "GET") return;
  if (u.pathname.startsWith("/api") || u.pathname.startsWith("/events") || u.pathname.startsWith("/cmd")) return;
  // rede primeiro (pega atualizações); cache se estiver offline
  e.respondWith(
    fetch(e.request).then(r => {
      const cp = r.clone();
      caches.open(CACHE).then(c => c.put(e.request, cp));
      return r;
    }).catch(() =>
      caches.match(e.request).then(m => m || caches.match("/"))
    )
  );
});
