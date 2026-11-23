// Offline support: always try the network first (so edits to words.txt show up),
// fall back to the saved copy when there's no signal.
const CACHE = "scots-dictionary-v16";
const FILES = ["./", "index.html", "words.txt", "topics.txt", "meanings.json", "data/usage-notes.json", "manifest.json", "icon-192.png", "icon-512.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(FILES)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  // Only the site's own files and its fonts – never GitHub API calls (they carry your key)
  const url = new URL(e.request.url);
  const ours = url.origin === self.location.origin;
  const font = /^(fonts\.googleapis\.com|fonts\.gstatic\.com)$/.test(url.hostname);
  if (!ours && !font) return;
  e.respondWith(
    fetch(e.request)
      .then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(e.request, copy));
        return res;
      })
      .catch(() => caches.match(e.request, { ignoreSearch: true }))
  );
});
