import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const read = p => readFileSync(new URL('../' + p, import.meta.url), 'utf8');
const app = read('src/App.jsx');
const main = read('src/main.jsx');
const config = read('vite.config.js');
const html = read('index.html');
const manifest = JSON.parse(read('public/manifest.webmanifest'));
const pack = JSON.parse(read('package.json'));

test('React and correct GitHub Pages base', () => {
  assert.match(main, /createRoot/);
  assert.match(config, /base:\s*['"]\/PhiPie\/['"]/);
  assert.equal(pack.dependencies.react, pack.dependencies['react-dom']);
  assert.equal(manifest.start_url, '/PhiPie/');
  assert.equal(manifest.scope, '/PhiPie/');
});
test('fictional node boundaries', () => {
  for (const name of ['Scout Pie','Professor Phi','Queso Relay','Dream Pie']) assert.ok(app.includes(name));
  for (const id of ['PHIPIE-DEMO-001','PHIPIE-DEMO-002','PHIPIE-DEMO-003','PHIPIE-DEMO-004']) assert.ok(app.includes(id));
  for (const phrase of ['SIMULATED','NOT PERFORMED','not a LightBridge optical transfer','No measured hops','PHIPIE-03']) assert.ok(app.toLowerCase().includes(phrase.toLowerCase()));
});
test('no data collection or direct network API in React app', () => {
  for (const forbidden of ['fetch(', 'XMLHttpRequest', 'localStorage', 'sessionStorage', 'getUserMedia(', 'geolocation', 'dangerouslySetInnerHTML', 'innerHTML']) {
    assert.ok(!app.includes(forbidden), 'forbidden capability: ' + forbidden);
  }
  assert.match(app, /notes.*useState/);
  assert.match(app, /maxLength=\{120\}/);
  assert.match(html, /%BASE_URL%/);
});
