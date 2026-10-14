import { useMemo, useState } from 'react';
import builtInCapsule from './capsules/scout-grove.commons.json';
import { MAX_CAPSULE_BYTES, decodeCapsule, encodeCapsule } from './capsule.mjs';

const SOURCE = encodeCapsule(builtInCapsule);

function downloadText(text, filename) {
  const url = URL.createObjectURL(new Blob([text], { type: 'application/json;charset=utf-8' }));
  try {
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.append(a);
    a.click();
    a.remove();
  } finally {
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
}

export default function CapsuleExplorer() {
  const [capsule, setCapsule] = useState(() => decodeCapsule(SOURCE));
  const [raw, setRaw] = useState(SOURCE);
  const [roomId, setRoomId] = useState('clearing');
  const [discovered, setDiscovered] = useState(false);
  const [message, setMessage] = useState('Bundled fictional district loaded. No private Porch data or remote fetch.');
  const [digest, setDigest] = useState('');

  const district = capsule?.district ?? null;
  const currentRoom = useMemo(() => district?.rooms.find(room => room.id === roomId) ?? null, [district, roomId]);

  function move(to) {
    if (!currentRoom?.exits.some(exit => exit.to === to)) return; // only paths the room declares
    setRoomId(to);
    setDiscovered(false);
    setMessage('Moved within the local capsule. No network request.');
  }

  async function onImport(event) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    // Fail closed on any invalid document, rather than silently continuing with old data.
    setCapsule(null);
    setRaw('');
    setRoomId('');
    setDiscovered(false);
    setDigest('');
    if (file.size > MAX_CAPSULE_BYTES || file.size < 100) {
      setMessage('Capsule refused: file must be 100 bytes to 64 KiB.');
      return;
    }
    try {
      const nextRaw = await file.text();
      const next = decodeCapsule(nextRaw);
      setCapsule(next);
      setRaw(nextRaw);
      setRoomId(next.district.start_room);
      setMessage('Validated local import: ' + next.district.title + '. Data-only preview, not publication approval.');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Capsule refused.');
    }
  }

  async function onDownload() {
    if (!capsule || !raw) return;
    try {
      downloadText(raw, capsule.district.district_id + '.commons');
      if (globalThis.crypto?.subtle) {
        const hash = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(raw));
        setDigest(Array.from(new Uint8Array(hash), b => b.toString(16).padStart(2, '0')).join(''));
      } else {
        setDigest('');
      }
      setMessage('Portable JSON capsule prepared locally. A digest checks content bytes only; no identity was authenticated.');
    } catch {
      setMessage('The browser refused to prepare this file. The world remains available in this tab.');
    }
  }

  function restore() {
    const next = decodeCapsule(SOURCE);
    setCapsule(next);
    setRaw(SOURCE);
    setRoomId(next.district.start_room);
    setDiscovered(false);
    setDigest('');
    setMessage('Bundled fictional district restored. Nothing was fetched or installed.');
  }

  return <section className="commons-section section-space" id="commons" aria-labelledby="commons-title">
    <div className="section-heading">
      <div>
        <p className="eyebrow">02 / COMMONS POCKET EDITION · C1 CAPSULE</p>
        <h2 id="commons-title">A whole world, <em>with a handle.</em></h2>
        <p>Step inside an explorable fictional Commons district packed as a portable, bounded JSON file. This entire exhibit runs in your browser.</p>
      </div>
      <span className="section-symbol" aria-hidden="true">⌂</span>
    </div>
    <div className="capsule-shell">
      <div className="capsule-topbar">
        <span>✳ COMMONS / LOCAL VISITOR DOOR</span>
        <strong>OFFLINE DATA · NOT A LIVE PORCH</strong>
      </div>
      <div className="capsule-body">
        <div className="capsule-scene">
          <div className="pocket-sky" aria-hidden="true"><span className="pocket-moon">☾</span><span className="pocket-hill a" /><span className="pocket-hill b" /></div>
          <div className="pocket-village">
            <div className="village-title"><small>YOU ARE VISITING</small><h3>{district?.title ?? 'The door is closed'}</h3><p>{district?.subtitle ?? 'The current import was refused.'}</p></div>
            {district && <div className="village-sites" aria-label="District locations">
              {district.rooms.map(room => <button key={room.id} type="button"
                aria-pressed={room.id === roomId}
                onClick={() => {
                  if (room.id === roomId) return;
                  if (!currentRoom?.exits.some(exit => exit.to === room.id)) {
                    setMessage('That location is not connected to this room. Use a marked path.');
                    return;
                  }
                  move(room.id);
                }}
                className={'village-site' + (room.id === roomId ? ' arrived' : '')}>
                <span aria-hidden="true">{room.symbol}</span><small>{room.title}</small>
              </button>)}
            </div>}
          </div>
          <div className="scene-foot"><span>SCENE: ILLUSTRATIVE ONLY</span><span>NO GPS / NO ACTUAL NEIGHBORS</span></div>
        </div>
        <div className="capsule-panel">
          {district && currentRoom ? <>
            <p className="eyebrow">ROOM / {currentRoom.kind.toUpperCase()} · {capsule.bootstrap.candidate_id}</p>
            <h3><span>{currentRoom.symbol}</span> {currentRoom.title}</h3>
            <p className="capsule-description">{currentRoom.description}</p>
            <button type="button" className="btn primary" onClick={() => setDiscovered(true)}>Inspect this place ✦</button>
            {discovered && <div className="capsule-discovery" aria-live="polite"><small>STORY FRAGMENT · FICTIONAL</small><p>{currentRoom.discovery}</p></div>}
            <div className="capsule-exits">
              <p>CHOOSE A PATH</p>
              {currentRoom.exits.map(exit => <button type="button" key={exit.to} onClick={() => move(exit.to)}>{exit.label}<span aria-hidden="true">↗</span></button>)}
            </div>
            <p className="capsule-welcome">{district.welcome}</p>
          </> : <div role="alert" className="capsule-refusal"><h3>Closed door.</h3><p>That capsule did not pass the local C1 manifest checks. Nothing was loaded or executed.</p><button type="button" className="btn primary" onClick={restore}>Reopen bundled grove ↗</button></div>}
        </div>
      </div>
      <div className="capsule-tray">
        <div><span className="eyebrow">PORTABLE COMMONS CAPSULE</span><p>Download this district, then import that same <code>.commons</code> file to prove the local handoff. Import only files you choose.</p></div>
        <div className="capsule-tray-actions">
          <button type="button" className="btn outline" onClick={onDownload} disabled={!capsule}>Download .commons ↓</button>
          <label className="btn primary capsule-file-button">Import local capsule ↗
            <input type="file" accept=".commons,.json,application/json" onChange={onImport} aria-label="Choose a local Commons capsule file" />
          </label>
          <button type="button" className="btn quiet" onClick={restore}>Reset sample</button>
        </div>
      </div>
      <div className="capsule-status" role="status">{message}{digest && <p>SHA-256 (local file bytes): <code>{digest}</code></p>}</div>
    </div>
    <p className="capsule-limit"><strong>REALITY GATE / C1-C:</strong> A data-only portable Canopy envelope containing a Commons-shaped bootstrap and one virtual artifact. It does not yet load directly in the canonical Infinite Commons Python filesystem loader without an explicit unpack/export adapter. No BBS, Porch messaging, NBG model routing, PhiStream inference, LightBridge optical transfer, user accounts, publication rights, physical node, or network connection is involved.</p>
  </section>;
}
