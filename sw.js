/* Offline support. Lives at the REPO ROOT, not in reader/, and that is not arbitrary: a
   service worker can only intercept requests inside its own scope, and the reader loads
   ../STUDY/te2rom.js, ../GRAMMAR_LAB/verbs.js, ../ministories/lr/*.mp3 and
   ../intensive/audio/words/*.mp3 — all of it above reader/. Registered from reader/index.html
   at scope '../', a worker in reader/ would have caught the page and none of its data.

   TWO CACHES, DELIBERATELY, AND ONLY ONE IS VERSIONED
   The shell — markup, CSS, JS, the baked datasets — is 2.2 MB and changes whenever the site is
   rebuilt, so it carries a version and is thrown away on each bump. Audio is up to 197 MB and
   never changes once generated, so it lives in an unversioned cache that survives every code
   update. Versioning them together would re-download a flight's worth of audio because a CSS
   file moved.

   RANGE REQUESTS ARE THE WHOLE DIFFICULTY
   Safari does not fetch an audio file; it asks for byte ranges, and the Cache API cannot store
   a 206 Partial Content response. Passing those through means audio never caches and the
   offline player is silent. So a media request is served by holding the FULL response in the
   cache and slicing it here, synthesising the 206 the player expects. */

const SHELL = 'rtt-shell-v3';
const AUDIO = 'rtt-audio';          // unversioned on purpose — see above

const at = (p) => new URL(p, self.registration.scope).toString();

/* The app shell and every baked dataset. Small enough to take in one go on install, which is
   what makes the reader work on a plane without anyone having thought to prepare it. */
const PRECACHE = [
  './',
  'index.html',
  'manifest.webmanifest',
  'reader/',
  'reader/index.html',
  'reader/assets/reader.css',
  'reader/assets/app.js',
  'reader/assets/levels.js',
  'reader/assets/sync.js',
  'reader/assets/aidict.js',
  'reader/data/ministories.js',
  'reader/data/intensive.js',
  'reader/data/hp1-discussion.js',
  'reader/data/poa.js',
  'STUDY/assets/te2rom.js',
  'STUDY/assets/progress.js',
  'GRAMMAR_LAB/data/verbs.js',
  'GRAMMAR_LAB/data/engine.js',
  'chrome-extension/src/colloquial.js',
].map(at);

const isAudio = (url) => /\.(mp3|m4a|wav|ogg|opus|aac)$/i.test(new URL(url).pathname);
const isFont = (url) => /fonts\.(googleapis|gstatic)\.com$/.test(new URL(url).host);

self.addEventListener('install', (e) => {
  e.waitUntil((async () => {
    const cache = await caches.open(SHELL);
    /* One at a time rather than addAll: addAll rejects as a unit, so a single renamed file
       would leave the whole shell uncached and the site would look like it had no offline
       support at all. */
    await Promise.all(PRECACHE.map(async (u) => {
      try { await cache.add(new Request(u, { cache: 'reload' })); } catch (_) { /* skip */ }
    }));
    self.skipWaiting();
  })());
});

self.addEventListener('activate', (e) => {
  e.waitUntil((async () => {
    const keep = new Set([SHELL, AUDIO]);
    for (const k of await caches.keys()) {
      if (!keep.has(k)) await caches.delete(k);
    }
    await self.clients.claim();
  })());
});

/* Serve a media file from cache, honouring whatever byte range was asked for. */
async function audioResponse(request) {
  const cache = await caches.open(AUDIO);
  const key = new Request(request.url);        // no Range header: the full-file cache key
  let full = await cache.match(key);

  if (!full) {
    try {
      const fresh = await fetch(request.url);  // deliberately un-ranged, so we store it whole
      if (!fresh || !fresh.ok) return fetch(request);
      await cache.put(key, fresh.clone());
      full = fresh;
    } catch (_) {
      return new Response('', { status: 504, statusText: 'offline, not downloaded' });
    }
  }

  const range = request.headers.get('range');
  if (!range) return full;

  const buf = await full.clone().arrayBuffer();
  const m = /bytes=(\d*)-(\d*)/.exec(range) || [];
  let start = m[1] ? parseInt(m[1], 10) : 0;
  let end = m[2] ? parseInt(m[2], 10) : buf.byteLength - 1;
  if (!Number.isFinite(start) || start >= buf.byteLength) {
    return new Response('', { status: 416, headers: { 'Content-Range': `bytes */${buf.byteLength}` } });
  }
  end = Math.min(end, buf.byteLength - 1);
  const slice = buf.slice(start, end + 1);
  return new Response(slice, {
    status: 206,
    statusText: 'Partial Content',
    headers: {
      'Content-Type': full.headers.get('Content-Type') || 'audio/mpeg',
      'Content-Length': String(slice.byteLength),
      'Content-Range': `bytes ${start}-${end}/${buf.byteLength}`,
      'Accept-Ranges': 'bytes',
    },
  });
}

async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const hit = await cache.match(request, { ignoreSearch: false });
  const net = fetch(request).then(async (res) => {
    if (res && res.ok) await cache.put(request, res.clone());
    return res;
  }).catch(() => null);
  return hit || (await net) || new Response('', { status: 504 });
}

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = req.url;

  if (isAudio(url)) { e.respondWith(audioResponse(req)); return; }

  /* Google's font CSS and the font files it pulls. Opaque cross-origin responses cache fine
     for this purpose; we only ever hand them straight back. */
  if (isFont(url)) {
    e.respondWith((async () => {
      const cache = await caches.open(SHELL);
      const hit = await cache.match(req);
      if (hit) return hit;
      try {
        const res = await fetch(req);
        await cache.put(req, res.clone());
        return res;
      } catch (_) {
        return new Response('', { status: 504 });
      }
    })());
    return;
  }

  if (new URL(url).origin !== self.location.origin) return;

  /* A navigation that cannot reach the network falls back to the reader, so tapping the home
     screen icon on a plane opens the app instead of a browser error. */
  if (req.mode === 'navigate') {
    e.respondWith((async () => {
      try {
        const res = await fetch(req);
        if (res && res.ok) {
          const cache = await caches.open(SHELL);
          await cache.put(req, res.clone());
        }
        return res;
      } catch (_) {
        const cache = await caches.open(SHELL);
        return (await cache.match(req)) || (await cache.match(at('reader/index.html')))
            || (await cache.match(at('index.html')))
            || new Response('Offline and not cached.', { status: 504 });
      }
    })());
    return;
  }

  e.respondWith(staleWhileRevalidate(req, SHELL));
});

/* The page asks what is stored so the Offline panel can show it without guessing. */
self.addEventListener('message', (e) => {
  if (e.data && e.data.type === 'audio-cache-name') {
    e.source.postMessage({ type: 'audio-cache-name', name: AUDIO });
  }
});
