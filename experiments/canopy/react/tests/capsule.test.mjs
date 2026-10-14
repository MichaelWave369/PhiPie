import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { decodeCapsule, encodeCapsule, ARTIFACT_PATH, MAX_CAPSULE_BYTES } from '../src/capsule.mjs';

const source = readFileSync(new URL('../src/capsules/scout-grove.commons.json', import.meta.url), 'utf8');
const copy = () => JSON.parse(source);
const mutate = fn => { const obj = copy(); fn(obj); return JSON.stringify(obj); };
const roomsOf = o => o.artifacts[ARTIFACT_PATH].rooms;
const refuse = (value, pattern = /Capsule refused:/) => assert.throws(() => decodeCapsule(value), pattern);

test('bundled portable capsule validates with original Commons bootstrap layout', () => {
  const parsed = decodeCapsule(source);
  assert.equal(parsed.format, 'phipie.canopy.capsule.v0.1');
  assert.equal(parsed.bootstrap.target, 'commons');
  assert.equal(parsed.bootstrap.artifacts[0].path, ARTIFACT_PATH);
  assert.equal(parsed.bootstrap.artifacts[0].load_order, 10);
  assert.equal(parsed.district.provenance, 'SIMULATED');
  assert.equal(parsed.district.rooms.length, 5);
  assert.equal(parsed.district.start_room, 'clearing');
  assert.deepEqual(decodeCapsule(encodeCapsule(copy())).district, parsed.district);
  assert.notEqual(parsed.district, copy().artifacts[ARTIFACT_PATH]);
});

test('bad structure, unknown authority claims and modified paths fail closed', () => {
  refuse('not json');
  refuse('{}');
  refuse(mutate(o => o.format = 'dangerous.execute.v1'));
  refuse(mutate(o => o.bootstrap.channel_name = 'owner-secret'));
  refuse(mutate(o => o.bootstrap.artifacts[0].path = '../../secret.json'));
  refuse(mutate(o => o.bootstrap.artifacts[0].required = false));
  refuse(mutate(o => o.bootstrap.artifacts[0].load_order = 1));
  refuse(mutate(o => o.artifacts[ARTIFACT_PATH].provenance = 'VERIFIED'));
  refuse(mutate(o => o.artifacts[ARTIFACT_PATH].publication_mode = 'owner-authorized'));
  refuse(mutate(o => o.bootstrap.artifacts.push(o.bootstrap.artifacts[0])));
  refuse(mutate(o => o.artifacts[ARTIFACT_PATH].remote_url = 'https://example.org'));
});

test('room identity, navigation graph, sizes and text are bounded', () => {
  refuse(mutate(o => roomsOf(o)[1].id = 'clearing'));
  refuse(mutate(o => roomsOf(o)[1].id = '../admin'));
  refuse(mutate(o => roomsOf(o)[0].exits[0].to = 'unknown'));
  refuse(mutate(o => roomsOf(o)[0].exits[0].to = 'clearing'));
  refuse(mutate(o => roomsOf(o)[0].exits.push(roomsOf(o)[0].exits[0])));
  refuse(mutate(o => o.artifacts[ARTIFACT_PATH].start_room = 'missing'));
  refuse(mutate(o => roomsOf(o)[0].description = '<script>bad</script>'));
  refuse(mutate(o => roomsOf(o)[0].description = 'javascript:alert(1)'));
  refuse(mutate(o => roomsOf(o)[0].description = '\u202Eevil'));
  refuse(mutate(o => roomsOf(o)[0].discovery = 'X'.repeat(321)));
  refuse(mutate(o => roomsOf(o)[0].symbol = '<svg/>'));
  refuse(mutate(o => roomsOf(o)[0].payload = {grant:'root'}));
  refuse(mutate(o => { roomsOf(o)[1].exits = [{to:'clearing',label:'exit'}]; roomsOf(o)[0].exits = roomsOf(o)[0].exits.filter(e=>e.to!=='library'); roomsOf(o)[4].exits = roomsOf(o)[4].exits.filter(e=>e.to!=='library'); }));
});

test('large and surprise fields do not get a preview', () => {
  refuse(' '.repeat(MAX_CAPSULE_BYTES + 1));
  refuse(mutate(o => o['__proto__'] = { malware: true }) + 'extra');
  refuse(mutate(o => { Object.defineProperty(o, '__proto__', {value:{elevate: true},enumerable:true}); }));
  refuse(mutate(o => { o.bootstrap.debug = true; }));
  refuse(mutate(o => { o.artifacts[ARTIFACT_PATH].rooms.push(...Array(4).fill({...roomsOf(o)[0]})); }));
});

test('source and UI keep the deployment isolated from hardware authority', () => {
  const ui = readFileSync(new URL('../src/CapsuleExplorer.jsx', import.meta.url), 'utf8');
  const root = readFileSync(new URL('../src/App.jsx', import.meta.url), 'utf8');
  const precache = readFileSync(new URL('../scripts/precache.mjs', import.meta.url), 'utf8');
  assert.match(root, /<CapsuleExplorer\s*\/>/);
  assert.match(root, /href="#commons"/);
  assert.match(ui, /type="file"/);
  assert.match(ui, /decodeCapsule/);
  assert.match(ui, /setCapsule\(null\)/);
  assert.match(ui, /No BBS, Porch messaging/);
  assert.match(precache, /assets\//); // JSON is bundled by Vite, no remote runtime fetch
  for (const forbidden of ['getUserMedia(', 'geolocation', 'WebSocket', 'eval(', 'dangerouslySetInnerHTML']) {
    assert.ok(!ui.includes(forbidden), 'unexpected capability: ' + forbidden);
  }
});
