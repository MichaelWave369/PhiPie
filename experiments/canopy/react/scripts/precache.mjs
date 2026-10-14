// Generated offline service worker for the static Vite output.
import { readdir, readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';

const dist = new URL('../dist/', import.meta.url);
async function walk(dir, prefix = '') {
  const entries = await readdir(dir, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const relative = (prefix ? prefix + '/' : '') + entry.name;
    if (entry.isDirectory()) files.push(...await walk(new URL(relative + '/', dist), relative));
    else if (entry.isFile() && entry.name !== 'sw.js') files.push(relative);
  }
  return files;
}
const all = (await walk(dist)).sort();
for (const required of ['index.html', 'manifest.webmanifest', 'favicon.svg']) {
  if (!all.includes(required)) throw new Error('Missing shell: ' + required);
}
const files = all.filter(x => ['index.html', 'manifest.webmanifest', 'favicon.svg'].includes(x) || x.startsWith('assets/'));
if (!files.some(x => x.endsWith('.js')) || !files.some(x => x.endsWith('.css'))) {
  throw new Error('Missing Vite assets');
}
const digest = createHash('sha256');
for (const f of files) { digest.update(f); digest.update(await readFile(new URL(f, dist))); }
const cacheName = 'phipie-canopy-react-' + digest.digest('hex').slice(0, 16);
const lines = [
  '/* Auto-generated offline shell. Scope: GitHub Pages /PhiPie/ only. */',
  'const CACHE = ' + JSON.stringify(cacheName) + ';',
  'const FILES = ' + JSON.stringify(files) + ';',
  "const scope = self.registration.scope;",
  "self.addEventListener('install', event => {",
  "  event.waitUntil((async () => {",
  "    const cache = await caches.open(CACHE);",
  "    await cache.addAll(FILES.map(file => new URL(file, scope).href));",
  "    await self.skipWaiting();",
  "  })());",
  "});",
  "self.addEventListener('activate', event => {",
  "  event.waitUntil((async () => {",
  "    const names = await caches.keys();",
  "    await Promise.all(names.filter(n => n.startsWith('phipie-canopy-react-') && n !== CACHE).map(n => caches.delete(n)));",
  "    await self.clients.claim();",
  "  })());",
  "});",
  "self.addEventListener('fetch', event => {",
  "  const request = event.request;",
  "  const url = new URL(request.url);",
  "  if (request.method !== 'GET' || url.origin !== self.location.origin || !url.href.startsWith(scope)) return;",
  "  event.respondWith((async () => {",
  "    const cache = await caches.open(CACHE);",
  "    const cached = await cache.match(request);",
  "    if (cached) return cached;",
  "    try {",
  "      const response = await fetch(request);",
  "      if (response.ok && response.type === 'basic') await cache.put(request, response.clone());",
  "      return response;",
  "    } catch {",
  "      if (request.mode === 'navigate') return await cache.match(new URL('index.html', scope).href) || Response.error();",
  "      return Response.error();",
  "    }",
  "  })());",
  "});",
  ""
];
await writeFile(new URL('sw.js', dist), lines.join('\n'), 'utf8');
console.log('Offline shell: ' + files.length + ' first-party files, ' + cacheName);
