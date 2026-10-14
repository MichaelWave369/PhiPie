# Canopy Commons Capsule C1 · portable fictional district

**Status:** browser-only data handoff candidate. No hardware qualification, remote fetch, trust authority, visitor identity, model inference or physical mesh claims.

## Why

The Canopy C1 React exhibit already has four fictional lunchbox personalities. This milestone adds one *actual portable data file* representing a tiny fictional Commons district: Lantern Clearing, Professor Phi's Library, Queso's Relay, the Lunchbox Workshop and Dream Pie's Garden.

The file is self-contained, readable, directly importable/exportable through the browser file picker, and validatable without network access. No code, model weights, API URLs, or private Porch data can be packaged.

## Capsule shape

The source is \`react/src/capsules/scout-grove.commons.json\`.

\`\`\`json
{
  "format": "phipie.canopy.capsule.v0.1",
  "bootstrap": {
    "target": "commons",
    "channel_name": "stable",
    "candidate_id": "canopy-scout-grove-v01",
    "artifacts": [{
      "name": "commons_manifest",
      "path": "commons_data/artifacts/manifest.json",
      "required": true,
      "load_order": 10
    }]
  },
  "artifacts": {
    "commons_data/artifacts/manifest.json": {
      "schema": "phipie.canopy.district.v0.1",
      "district_id": "scout-grove",
      "title": "The Lantern Grove",
      "subtitle": "a tiny fictional neighborhood",
      "welcome": "hello",
      "provenance": "SIMULATED",
      "publication_mode": "fictional-public-sample",
      "start_room": "clearing",
      "rooms": ["...strictly typed room objects, see sample..."]
    }
  }
}
\`\`\`

The \`bootstrap\` names, required marker, relative path and deterministic load order match the conceptual conventions in [Infinite Commons](https://github.com/MichaelWave369/Infinite-Commons/blob/main/docs/bootstrap_contract.md). **Important difference:** the canonical Commons Python loader consumes separate *files in a repository tree*. Our **single-file envelope with a virtual artifact map** is a new, Canopy-specific portable format, and the Python Commons loader cannot read it directly. An explicit unpack/export and cross-repository interoperability test must precede claims that it can.

## Rules

1. UTF-8 JSON only, <=64 KiB, no executable extensions or dependencies.
2. Exact-key allowlists for envelope, bootstrap, artifact reference, district, rooms and exits. Unknown/missing fields refuse.
3. Exactly one required manifest artifact with frozen path and load order 10. No arbitrary file path resolution, URL fetching, origin selection, plug-in loading or scripts.
4. 2–8 rooms with safe unique slugs; 1–4 declared exits per room, all endpoints exist, no self-exits or duplicate targets. All rooms reachable from start.
5. Text limits, no control/bidi override characters, no HTML markup or URL-like payloads; React renders all content as text.
6. \`SIMULATED\` provenance and \`fictional-public-sample\` publication mode are mandatory. These are **data labels**, not content ownership, signatures, proof of truth, or public-sharing authority.
7. File import is an explicit local user action. On validation failure, the active capsule is cleared; the visitor can explicitly restore the built-in grove. No silent fall-through to a different package.
8. User notes remain separately in tab memory and are *not* exported inside the capsule.
9. A local SHA-256 digest of exported capsule bytes, if available, detects changes; it does not prove provenance, consent, authenticity, or transport success.
10. The builtin JSON is imported into the Vite code bundle for Pages, so it is available after the static shell has been successfully cached. No live local hardware service or cloud inference is called.

## Try it

Open PhiPie Canopy React, scroll to **Pocket Commons**, navigate via labeled exits, inspect the clues, download the \`.commons\` file, then import the very same file using the native chooser. Try importing an invalid JSON file: the world closes, shows a refusal, and can be restored explicitly.

From \`experiments/canopy/react/\` run:

\`\`\`sh
npm ci
npm run verify
\`\`\`

\`tests/capsule.test.mjs\` exercises roundtrip, graph validity, malicious paths, unknown fields, status forgery, oversized texts, bad provenance, HTML-like content, and intentionally broken navigation. The existing React build and Pages workflow remain unchanged and run the new tests through \`npm run test\`.

## Future gates, not C1

- **C2-Capsule:** optional local *unpack* adapter generating canonical \`commons_data/bootstrap/latest_contract.json\` and \`commons_data/artifacts/manifest.json\`; cross-repo tests with the actual Commons Python loader. A browser file picker cannot silently write a filesystem tree.
- **C3-Capsule:** operator-curated public export / signed provenance separate from consent and publication grants.
- **C4-Capsule:** real PhiPie local HTTP hosting on qualified hardware and permissioned discovery; real-device/offline measurements.
- **C5-Capsule:** scoped Porch messaging and tested LightBridge optical packet delivery as separate explicit transports.

**C1 does not install, trust or publish anything. Capability is not authority.**
