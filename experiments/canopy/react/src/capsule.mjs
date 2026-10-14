// Canopy Commons Capsule C1: original single-file adapter, data only.
// The Infinite Commons Python loader expects a repository tree; this portable
// envelope embeds that deterministic bootstrap and one virtual artifact.
export const CAPSULE_FORMAT = 'phipie.canopy.capsule.v0.1';
export const MANIFEST_SCHEMA = 'phipie.canopy.district.v0.1';
export const ARTIFACT_PATH = 'commons_data/artifacts/manifest.json';
export const MAX_CAPSULE_BYTES = 65536;

const unsafe = /[\u0000-\u001f\u007f-\u009f\u202a-\u202e\u2066-\u2069]/u;
const slug = /^[a-z][a-z0-9-]{0,39}$/;
const formats = new Set(['plaza', 'library', 'relay', 'studio', 'garden']);
const symbols = new Set(['✳', '✦', '✺', '◇', '☾']);

function fail(message) { throw new Error('Capsule refused: ' + message); }
function object(value, label, keys) {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) fail(label + ' must be an object');
  const own = Object.keys(value);
  if (own.length !== keys.length || keys.some(k => !Object.hasOwn(value, k))) fail(label + ' has missing or unknown fields');
  return value;
}
function string(value, label, max = 280) {
  if (typeof value !== 'string' || value.length < 1 || value.length > max || unsafe.test(value)) fail(label + ' has invalid text');
  // Everything renders as React text. Still decline URL/markup-like extensions
  // to avoid accidentally creating an executable or link-enabled schema later.
  if (/<|>|(?:https?:\/\/|javascript:|data:)/i.test(value)) fail(label + ' cannot contain markup or URLs');
  return value;
}
function id(value, label) {
  string(value, label, 40);
  if (!slug.test(value)) fail(label + ' is not a safe identifier');
  return value;
}
function enumValue(value, label, allowed) {
  if (!allowed.has(value)) fail(label + ' is unsupported');
  return value;
}
function array(value, label, min, max) {
  if (!Array.isArray(value) || value.length < min || value.length > max) fail(label + ' count is invalid');
  return value;
}

export function decodeCapsule(raw) {
  if (typeof raw !== 'string') fail('input must be UTF-8 JSON text');
  const size = new TextEncoder().encode(raw).byteLength;
  if (size > MAX_CAPSULE_BYTES) fail('64 KiB limit exceeded');
  if (size < 100) fail('document is incomplete');
  let input;
  try { input = JSON.parse(raw); } catch { fail('JSON cannot be parsed'); }
  object(input, 'capsule', ['format', 'bootstrap', 'artifacts']);
  if (input.format !== CAPSULE_FORMAT) fail('unknown capsule format');

  const bootstrap = object(input.bootstrap, 'bootstrap', ['target', 'channel_name', 'candidate_id', 'artifacts']);
  if (bootstrap.target !== 'commons' || bootstrap.channel_name !== 'stable') fail('unsupported Commons target or channel');
  id(bootstrap.candidate_id, 'candidate_id');
  const refs = array(bootstrap.artifacts, 'bootstrap artifacts', 1, 1);
  const ref = object(refs[0], 'artifact reference', ['name', 'path', 'required', 'load_order']);
  if (ref.name !== 'commons_manifest' || ref.path !== ARTIFACT_PATH || ref.required !== true || ref.load_order !== 10) {
    fail('artifact path, priority or required flag does not match C1');
  }
  const artifacts = object(input.artifacts, 'embedded artifacts', [ARTIFACT_PATH]);
  const district = object(artifacts[ARTIFACT_PATH], 'district manifest', [
    'schema', 'district_id', 'title', 'subtitle', 'welcome', 'provenance',
    'publication_mode', 'start_room', 'rooms'
  ]);
  if (district.schema !== MANIFEST_SCHEMA || district.provenance !== 'SIMULATED' ||
      district.publication_mode !== 'fictional-public-sample') fail('unqualified publication or provenance');
  id(district.district_id, 'district_id');
  string(district.title, 'title', 90);
  string(district.subtitle, 'subtitle', 140);
  string(district.welcome, 'welcome', 280);
  id(district.start_room, 'start_room');

  const rooms = array(district.rooms, 'rooms', 2, 8);
  const known = new Set();
  for (const room of rooms) {
    object(room, 'room', ['id', 'kind', 'symbol', 'title', 'description', 'discovery', 'exits']);
    id(room.id, 'room id');
    if (known.has(room.id)) fail('duplicate room identifier');
    known.add(room.id);
    enumValue(room.kind, 'room kind', formats);
    enumValue(room.symbol, 'room symbol', symbols);
    string(room.title, 'room title', 70);
    string(room.description, 'room description', 360);
    string(room.discovery, 'room discovery', 320);
    array(room.exits, 'exits', 1, 4);
    const outgoing = new Set();
    for (const exit of room.exits) {
      object(exit, 'exit', ['to', 'label']);
      id(exit.to, 'exit target');
      string(exit.label, 'exit label', 65);
      if (outgoing.has(exit.to) || exit.to === room.id) fail('duplicate/self-directed exit');
      outgoing.add(exit.to);
    }
  }
  if (!known.has(district.start_room)) fail('entry room missing');
  for (const room of rooms) {
    for (const exit of room.exits) if (!known.has(exit.to)) fail('dangling room exit');
  }
  const seen = new Set([district.start_room]);
  const pending = [district.start_room];
  const roomsById = new Map(rooms.map(room => [room.id, room]));
  while (pending.length) {
    for (const exit of roomsById.get(pending.shift()).exits) {
      if (!seen.has(exit.to)) { seen.add(exit.to); pending.push(exit.to); }
    }
  }
  if (seen.size !== rooms.length) fail('unreachable room');
  // Return detached data only; no permissions, execution hooks or network URLs.
  const safe = JSON.parse(JSON.stringify(input));
  return Object.freeze({
    format: safe.format,
    bootstrap: Object.freeze(safe.bootstrap),
    district: Object.freeze(safe.artifacts[ARTIFACT_PATH])
  });
}

export function encodeCapsule(input) {
  // Validate rather than blessing arbitrary in-memory values.
  const raw = JSON.stringify(input, null, 2) + '\n';
  decodeCapsule(raw);
  return raw;
}
