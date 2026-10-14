# PhiPie Canopy React showcase · C1-R

**Status: interactive simulated exhibit. This is not a live PhiPie hardware/mesh/LightBridge integration.**

React + Vite GitHub Pages presentation for the original Canopy C1 concept. The zero-dependency original experiment remains at ../site/ unchanged.

## Run locally

Requires Node.js 22.12+.

From the repository root, change into experiments/canopy/react, then run npm install and npm run dev. Open the Vite local URL under /PhiPie/, typically http://127.0.0.1:5173/PhiPie/ .

Run npm run verify to run source tests, production build and Pages output checks. Run npm run preview to serve the production build under /PhiPie/.

## Deploy

The app is built by .github/workflows/canopy-pages.yml. After this PR merges into main, that workflow validates the sources, builds Vite assets, creates the offline cache and deploys to GitHub Pages.

**One-time setup:** On GitHub, open Settings → Pages → Build and deployment → Source: GitHub Actions. Intended URL after a successful deployment: https://michaelwave369.github.io/PhiPie/ . Do not call the URL live before verifying the actual build/deploy results.

## Working features

- React interface with four simulated nodes, stories, fictional neighborhood, LightBridge concept display and interactive field-guide steps
- Text postcard downloaded locally with SHA-256 digest where WebCrypto is available; a digest is not an identity signature
- In-tab kindness notes, at most 120 characters and never persisted or transmitted
- No visitor analytics, cookies, accounts, GPS, model inference or remote browser fetch from application code
- Same-origin service worker precaches generated Vite shell and is limited to /PhiPie/. Verify offline behavior on the intended device; a browser may refuse caching.

## Not present

The site does not broadcast an SSID, operate a real field node, measure a mesh, send animated QR frames, use a camera or authenticate a device. LightBridge is separate unreleased research. PHIPIE-03 remains a real-board qualification candidate, and C1-R changes no firmware, Pi images, or runtime qualification. GitHub Pages hosts a normal website, not a local discovery network.

## Evidence contract

Target: public, read-only GitHub Pages frontend at /PhiPie/.
Inputs: node, story step and ephemeral text note.
Outputs: browser React view and downloaded local postcard.
Failure: blocked service worker, digest or downloads may degrade locally, without acquiring new permissions.
Evidence: source tests, Vite production output, successful Actions Pages deployment and browser smoke test.
Unqualified: all hardware, optical transport, mesh, security review and emergency communications.

**People Above Profit · Ledger Above Ego · PhiOS loves you, bro.**

## Canopy Commons Capsule C1

The React page now has a **Pocket Commons** doorway with a real, original, portable JSON sample at \`src/capsules/scout-grove.commons.json\`. The UI can explore its five fiction-only rooms, export a single \`.commons\` file, import the selected file locally and reject invalid or oversized documents. Validation performs no code execution, storage or network calls.

A capsule embeds a **Commons-shaped** \`bootstrap\` (\`target: commons\`, deterministic artifact path and order) and an embedded virtual artifact. The canonical Infinite Commons Python loader consumes a **filesystem tree**, so a single-file Canopy capsule is **not plug-and-play compatible** with that loader. A separately reviewed and tested unpack adapter would be required before claiming compatibility.

See [the C1 capsule contract](../../CAPSULE_C1.md). This is not a live Porch, authenticated identity, real mesh, optical transfer, AI model, or content publication system.
