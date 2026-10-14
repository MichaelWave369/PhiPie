import { useEffect, useMemo, useState } from 'react';

const NODES = Object.freeze([
  {
    id: 'PHIPIE-DEMO-001', short: '01', slug: 'scout', name: 'Scout Pie',
    role: 'Trail guide', symbol: '✳', emoji: '🌲', color: '#b5d99a',
    location: 'Fern Hollow · fictional', quote: 'PhiOS loves you, bro.',
    message: 'Be curious. Be kind. Keep your boots muddy and your assumptions labeled.',
    storyTitle: 'The mossy crossroads',
    story: 'At a fork in a forest trail, three signs point toward CURIOSITY, KINDNESS, and SNACKS. Scout Pie recommends all three, preferably with enough drinking water. The little lunchbox is not a real emergency beacon. It is a reminder that good adventures start with an invitation.',
    fact: 'The neighboring dots on this map are imaginary. No radio measurements have been taken.'
  },
  {
    id: 'PHIPIE-DEMO-002', short: '02', slug: 'professor', name: 'Professor Phi',
    role: 'Curiosity keeper', symbol: '✦', emoji: '📚', color: '#f5cb87',
    location: 'The Old Oak · fictional', quote: 'The question is part of the treasure.',
    message: 'Collect a question, not a stranger’s data.',
    storyTitle: 'The library without walls',
    story: 'Under the oldest imaginary oak, a small metal box contains a library of tiny questions. Why do leaves know when to fall? How far does a thought travel? Professor Phi promises to mark guesses as guesses, and to keep facts with their sources.',
    fact: 'Offline content can be available after the site is cached, but this browser cannot infer the safety or identity of a physical node.'
  },
  {
    id: 'PHIPIE-DEMO-003', short: '03', slug: 'queso', name: 'Queso Relay',
    role: 'Chief of good dogs', symbol: '✺', emoji: '🐾', color: '#eaa47e',
    location: 'Bark Ridge · fictional', quote: 'Bark twice for distributed systems.',
    message: 'WOOF is a message. It is not cryptographic authentication.',
    storyTitle: 'A distinguished transmission',
    story: 'A dispatch arrives from Bark Ridge: WOOF. A second dispatch arrives: ALSO WOOF. The committee concludes that all visitors should be offered water and perhaps a tiny adventure. Queso signs neither message with a real identity key, because these are fictional dogs in a fictional network.',
    fact: 'A displayed node label is not a verified identity, and a checksum alone is not authentication.'
  },
  {
    id: 'PHIPIE-DEMO-004', short: '04', slug: 'dreamer', name: 'Dream Pie',
    role: 'Story weaver', symbol: '☾', emoji: '✨', color: '#c7b7ff',
    location: 'Moonlit Grove · fictional', quote: 'The forest remembers a good story.',
    message: 'Imagine freely. Label dreams honestly.',
    storyTitle: 'The postcard constellation',
    story: 'Once, four lunchboxes agreed to trade postcards instead of secrets. Each one kept its own little world, but they opened a door for curious travelers. Nobody had to hand over a name, a location history, or a password to enjoy the story.',
    fact: 'The postcard download on this site is a local file, not a LightBridge optical transfer.'
  }
]);

const FIELD_GUIDE = [
  ['DISCOVER', 'A trail visitor scans a printed QR or visits a future permissioned local portal. C2, not yet implemented here.', '01'],
  ['EXPLORE', 'The visitor meets a lunchbox character, enjoys a tiny tale, and sees a plainly fictional constellation of nodes.', '02'],
  ['COLLECT', 'A postcard is made on your device. The page can calculate its SHA-256, proving only the local bytes match that digest.', '03'],
  ['SHARE LIGHT', 'An opt-in LightBridge screen-to-camera transfer may deliver a bounded packet later, after real-device validation.', '04']
];

const BASE = import.meta.env.BASE_URL;
const REPO = 'https://github.com/MichaelWave369/PhiPie';
const LIGHTBRIDGE = 'https://github.com/MichaelWave369/LightBridge';

function useOnlineStatus() {
  const [online, setOnline] = useState(() => navigator.onLine);
  useEffect(() => {
    const update = () => setOnline(navigator.onLine);
    window.addEventListener('online', update);
    window.addEventListener('offline', update);
    return () => { window.removeEventListener('online', update); window.removeEventListener('offline', update); };
  }, []);
  return online;
}

function LunchboxIllustration({ node }) {
  return <div className="forest-stage" aria-label="Illustration of a retro PhiPie lunchbox in a moonlit forest" role="img">
    <div className="moon-halo" />
    <div className="forest-glow" />
    <div className="hill hill-back" />
    <div className="hill hill-front" />
    <div className="tree tree-left" /><div className="tree tree-right" />
    <div className="firefly ff-one" /><div className="firefly ff-two" /><div className="firefly ff-three" />
    <div className="box-assembly">
      <div className="lunch-handle" /><div className="lunch-shell">
        <span className="lunch-rivet rivet-left" /><span className="lunch-rivet rivet-right" />
        <span className="lunch-stars">✦ · ✧</span>
        <span className="lunch-label">PHIPIE<br /><b>CANOPY</b></span>
        <span className="lunch-badge" style={{ color: node.color }}>{node.symbol}</span>
        <span className="lunch-footer">FIELD UNIT · {node.short.padStart(3, '0')}</span>
        <span className="lunch-led"><span /></span>
      </div>
      <div className="ground-shadow" />
    </div>
    <div className="floating-label label-top"><span className="pulse-dot" /> CANOPY DEMO · NO REAL SIGNAL</div>
    <div className="floating-label label-bottom">Somewhere between science & a fairy tale.</div>
  </div>;
}

function SignalIcon() {
  return <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="M4 10a12 12 0 0 1 16 0M7 14a7 7 0 0 1 10 0M10 18a3 3 0 0 1 4 0"/><circle cx="12" cy="21" r="1" fill="currentColor" stroke="none"/></svg>;
}

function ShortNode({ item, active, onChoose }) {
  return <button type="button" className={'node-card' + (active ? ' selected' : '')} onClick={onChoose} aria-pressed={active}>
    <span className="node-card-icon" style={{ '--node-accent': item.color }}>{item.symbol}</span>
    <span className="node-card-copy"><strong>{item.name}</strong><small>{item.role}</small></span>
    <span className="node-card-arrow" aria-hidden="true">↗</span>
  </button>;
}

function App() {
  const [currentId, setCurrentId] = useState(NODES[0].id);
  const [storyOpen, setStoryOpen] = useState(false);
  const [notes, setNotes] = useState([]);
  const [input, setInput] = useState('');
  const [receipt, setReceipt] = useState('');
  const [activeStep, setActiveStep] = useState(0);
  const [installState, setInstallState] = useState('Online-only until the site is cached');
  const online = useOnlineStatus();
  const node = useMemo(() => NODES.find(n => n.id === currentId) ?? NODES[0], [currentId]);

  useEffect(() => {
    if (!import.meta.env.PROD || !('serviceWorker' in navigator)) return;
    let cancelled = false;
    navigator.serviceWorker.register(BASE + 'sw.js', { scope: BASE })
      .then(() => {
        if (!cancelled) setInstallState('Offline cache requested · verify after a reload');
      })
      .catch(() => {
        if (!cancelled) setInstallState('Offline cache unavailable on this browser');
      });
    return () => { cancelled = true; };
  }, []);

  function chooseNode(id) { setCurrentId(id); setStoryOpen(false); setReceipt(''); }

  async function savePostcard() {
    const text = [
      'Φ PHIPIE CANOPY · FICTIONAL NODE POSTCARD',
      'SIMULATED EXHIBIT · NOT A PHYSICAL NETWORK RECEIPT',
      '', node.name, node.id, node.role, node.location,
      '', node.quote, '', node.storyTitle, node.story,
      '', 'LightBridge optical transfer: NOT PERFORMED',
      'Identity authentication: NOT PERFORMED',
      'No visitor data collected by this app.',
      'People Above Profit · Ledger Above Ego'
    ].join('\n');
    const bytes = new TextEncoder().encode(text);
    let hash = 'Digest unavailable on this browser';
    if (globalThis.crypto?.subtle) {
      try {
        const buffer = await crypto.subtle.digest('SHA-256', bytes);
        hash = Array.from(new Uint8Array(buffer), b => b.toString(16).padStart(2, '0')).join('');
      } catch { hash = 'Digest unavailable on this browser'; }
    }
    try {
      const url = URL.createObjectURL(new Blob([bytes], { type: 'text/plain;charset=utf-8' }));
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = node.id.toLowerCase() + '-postcard.txt';
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      setReceipt('Local postcard prepared. SHA-256: ' + hash + '. This is a content digest, not an identity signature or optical transfer receipt.');
    } catch {
      setReceipt('The browser blocked the download. Try the story view instead; nothing was sent to a server.');
    }
  }

  function submitNote(event) {
    event.preventDefault();
    const text = input.trim().slice(0, 120);
    if (!text) return;
    setNotes(prev => [{ key: Date.now().toString(36) + '-' + prev.length, text }, ...prev].slice(0, 4));
    setInput('');
  }

  return <div className="page">
    <a className="skip-link" href="#main">Skip to the forest</a>
    <header className="masthead">
      <a className="wordmark" href="#main"><span className="phi-logo">Φ</span><span>PhiPie <b>Canopy</b></span></a>
      <nav aria-label="Site navigation">
        <a href="#discover">Discover</a><a href="#nodes">The Nodes</a><a href="#lightbridge">LightBridge</a>
        <a className="nav-github" href={REPO} target="_blank" rel="noopener noreferrer">GitHub ↗</a>
      </nav>
    </header>
    <main id="main">
      <section className="hero" id="discover">
        <div className="hero-copy">
          <div className="kicker"><span className="kicker-mark">✳</span> A LITTLE FOREST INTERNET, IN IMAGINATION</div>
          <h1>THE FOREST<br />HAS <em>A NETWORK</em><br />NOW<span className="period">.</span></h1>
          <p className="hero-description">Tiny computers. Old-school lunchboxes. Big-hearted ideas. Imagine discovering a whole neighborhood of friendly offline adventures hiding among the trees.</p>
          <div className="hero-actions"><a className="btn primary" href="#nodes">Meet the lunchboxes <span>↗</span></a><a className="btn quiet" href="#field-guide">How it could work ↓</a></div>
          <p className="hero-footnote"><span className="glow-dot" /> SIMULATION ONLY · NO LIVE RADIOS OR REAL FIELD NODES</p>
        </div>
        <LunchboxIllustration node={node} />
      </section>

      <section className="welcome-bar" aria-label="Invitation">
        <div><span className="hello-star">✺</span><span><small>MESSAGE FROM THE CANOPY</small><strong>“PhiOS loves you, bro.”</strong></span></div>
        <span className="welcome-end">NO ACCOUNT. NO DATA HARVESTING. JUST CURIOSITY.</span>
      </section>

      <section className="nodes-section section-space" id="nodes">
        <div className="section-heading"><div><p className="eyebrow">01 / YOUR FRIENDLY NEIGHBORHOOD</p><h2>Meet the <em>lunchboxes.</em></h2><p>Four imaginary personalities. Four tiny worlds. Select a node to explore. Nothing here connects to an actual device.</p></div><span className="section-symbol" aria-hidden="true">✳</span></div>
        <div className="node-layout">
          <div className="node-list">{NODES.map(item => <ShortNode key={item.id} item={item} active={item.id === node.id} onChoose={() => chooseNode(item.id)} />)}</div>
          <article className="terminal">
            <div className="terminal-header"><span><span className="terminal-dot" /> PHIPIE CANOPY // FIELD TERMINAL</span><span className="sim-tag">SIMULATED</span></div>
            <div className="terminal-main">
              <span className="mini-eyebrow">{node.id} · {node.role.toUpperCase()}</span>
              <div className="terminal-avatar" style={{ '--node-accent': node.color }}>{node.symbol}</div>
              <h3>{node.name}</h3><p className="node-quote">“{node.quote}”</p>
              <p className="node-message">{node.message}</p>
              <div className="node-meta"><span>LOCATION</span><strong>{node.location}</strong></div>
              <div className="node-meta"><span>STATUS</span><strong>Fictional character · no physical link</strong></div>
              <div className="node-controls"><button className="btn primary" type="button" onClick={() => setStoryOpen(v => !v)}>{storyOpen ? 'Close the story −' : 'Explore a story ↗'}</button><button className="btn outline" type="button" onClick={savePostcard}>Save a postcard ↓</button></div>
              {storyOpen && <div className="story-panel" aria-live="polite"><small>AN OFFLINE TALE</small><h4>{node.storyTitle}</h4><p>{node.story}</p></div>}
              {receipt && <div className="receipt" role="status">{receipt}</div>}
            </div>
            <div className="terminal-footer"><span>⌁ FIELD NOTE</span><p>{node.fact}</p></div>
          </article>
        </div>
      </section>

      <section className="field-section section-space" id="field-guide">
        <div className="section-heading"><div><p className="eyebrow">02 / THE ADVENTURE PROTOCOL</p><h2>Find a box. <em>Find a story.</em></h2><p>What might a real canopy adventure feel like? Tap a step below. All four are a concept roadmap, not claims of deployed features.</p></div></div>
        <div className="step-layout"><div className="step-rail">{FIELD_GUIDE.map(([title, , number], i) => <button key={number} type="button" aria-pressed={activeStep === i} className={'step' + (activeStep === i ? ' current' : '')} onClick={() => setActiveStep(i)}><span className="step-number">{number}</span><span>{title}</span><b aria-hidden="true">↗</b></button>)}</div><div className="step-display"><div className="step-outline" aria-hidden="true"><span>{FIELD_GUIDE[activeStep][2]}</span><span className="step-glyph">{['⌗','✺','✉','◇'][activeStep]}</span></div><p className="eyebrow">CANOPY FIELD GUIDE / STEP {FIELD_GUIDE[activeStep][2]}</p><h3>{FIELD_GUIDE[activeStep][0]}</h3><p>{FIELD_GUIDE[activeStep][1]}</p></div></div>
      </section>

      <section className="light-section section-space" id="lightbridge">
        <div className="light-copy"><p className="eyebrow">03 / THE OPTICAL POSSIBILITY</p><h2>What if the<br /><em>light carried stories?</em></h2><p>LightBridge is our separate experimental screen-to-camera transfer research. A future lunchbox could show animated QR frames to share small verified packets without a network.</p><div className="light-disclaimer"><span>!</span><p><b>Still a proposal.</b> This site does not transmit QR packets, control cameras, confirm device identity, or grant pairing authority. Real phones and screens must be tested first.</p></div><a href={LIGHTBRIDGE} target="_blank" rel="noopener noreferrer" className="text-link">Explore the LightBridge research ↗</a></div>
        <div className="optical-diagram" role="img" aria-label="Conceptual diagram from lunchbox display through light toward a phone camera. No transfer occurs."><div className="diagram-box"><span>Φ</span><small>DISPLAY</small></div><div className="diagram-air"><span>✧</span><span>·······</span><span>✧</span><small>VISIBLE LIGHT · CONCEPT</small></div><div className="diagram-phone"><div className="phone-camera" /><span className="fake-qr" aria-hidden="true"><i /><i /><i /><i /><i /><i /><i /><i /><i /></span><small>RECEIVER</small></div></div>
      </section>

      <section className="bottom-section section-space">
        <div className="local-ledger"><p className="eyebrow">04 / THE KINDNESS LEDGER</p><h2>Leave something <em>good.</em></h2><p>A tiny note for this visit, held only in your current tab. It disappears on refresh, isn't shared, and isn't stored on GitHub.</p>
          <form onSubmit={submitNote}><label htmlFor="kindness">A NOTE FOR THE GROVE (MAX 120 CHARACTERS)</label><textarea id="kindness" maxLength={120} rows={3} value={input} onChange={event => setInput(event.target.value)} placeholder="The moss would like you to drink some water…" /><div className="form-footer"><small>{input.length}/120</small><button type="submit" className="btn primary" disabled={!input.trim()}>Add a little kindness +</button></div></form>
          <ul className="notes" aria-live="polite">{notes.map(n => <li key={n.key}>✳ <span>{n.text}</span></li>)}{notes.length === 0 && <li className="notes-empty">No notes in this tab yet. The forest is listening politely.</li>}</ul>
        </div>
        <aside className="network-panel"><div className="network-panel-top"><span><SignalIcon /> NEIGHBORHOOD MAP</span><strong>STORY MODE ONLY</strong></div><div className="mock-map" aria-label="Fictional neighborhood diagram, not geographic or radio coverage map">{NODES.map((n, i) => <button type="button" key={n.id} className={'map-node map-node-' + i + (n.id === node.id ? ' active' : '')} onClick={() => {chooseNode(n.id); document.getElementById('nodes')?.scrollIntoView({behavior:'smooth'});}} aria-label={'Select ' + n.name}><span>{n.symbol}</span><small>{n.name}</small></button>)}<div className="map-line map-line-a" /><div className="map-line map-line-b" /><div className="map-line map-line-c" /></div><p>No measured hops, real coordinates, Wi-Fi discovery or mesh traffic. The nodes are story characters.</p><p className="cache-status"><span className={online ? 'glow-dot' : 'glow-dot dim'} /> Browser reports {online ? 'online' : 'offline'}. {installState}.</p></aside>
      </section>
      <div className="reality"><strong>REALITY GATE / C1-R</strong><span>This is an imaginative, locally executed React showcase. Its nodes, messages, signals and map are simulated. PhiPie PHIPIE-03 hardware qualification, a functioning Wi-Fi mesh, a QR discovery system, and LightBridge device transfer are not established by this site. Please do not place physical equipment in forests without the property manager's permission.</span></div>
    </main>
    <footer className="footer"><div><span className="phi-logo">Φ</span><span>PHIPIE CANOPY<br /><small>THE FOREST HAS A NETWORK NOW. (IN OUR IMAGINATION.)</small></span></div><p>PEOPLE ABOVE PROFIT · LEDGER ABOVE EGO<br />MADE FOR CURIOUS HUMANS AND VERY GOOD DOGS.</p><a href={REPO} target="_blank" rel="noopener noreferrer">SOURCE CODE ↗</a></footer>
  </div>;
}

export default App;
