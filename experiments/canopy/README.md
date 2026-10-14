# PhiPie Canopy — C1 offline lunchbox exhibit

**Status: C1 STATIC CONCEPT / NO HARDWARE OR NETWORK AUTHORITY.**

A playful, original browser-only exhibit imagining a network of retro lunchboxes that share little offline adventures and kindness. This is an optional experiment inside PhiPie, **not** a PhiOS release, real PhiPie boot qualification, physical-radio driver, mesh router, visitor tracker, production captive portal, or LightBridge integration.

## Run it

From the repository root:

```sh
python -m http.server 8000 --directory experiments/canopy/site
```

Then browse to http://127.0.0.1:8000/ . The page loads only local HTML, CSS and JavaScript; disconnect from the internet to verify. You can also open the HTML file directly in a modern browser, although the HTTP loopback route is best for consistent browser behavior.

To run dependency-free static tests:

```sh
python -m unittest discover -s experiments/canopy/tests -v
```

## C1 contract

| Boundary | C1 |
| --- | --- |
| Target | Standalone browser, optionally served on loopback |
| Inputs | Selection of four *fictional* nodes, temporary guest note up to 120 characters |
| Outputs | Locally rendered story, fictional neighbor list, downloadable plain-text postcard |
| Privacy | No external requests, cookies, telemetry, geolocation or permanent storage; notes last only until refresh |
| Failures | Unsupported local browser or blocked downloads do not grant new capabilities; no remote fallback |
| Evidence | Static tests, review of network panel in browser offline, screenshots of UI, manual postcard verification |
| Unqualified | Hardware, battery, RF, Wi-Fi AP, outdoor deployment, QR discovery, camera permissions, LightBridge transfers, security claims, emergency coverage |

**Node IDs are simulated display labels, not PhiOS/Covenant identities.**
**Fictional neighbors are not observed links or route measurements.**
**Optical data integrity is not identity, consent, authorization, or verified truth.**

## Later small rungs (not implemented)

- **C2: QR discovery.** Printed static QR should point to a permissioned local AP portal only after a real AP exists. Offline QR labels and local-only HTTP need device-specific phone testing. Merely broadcasting an SSID will not reliably present a greeting.
- **C3: LightBridge handoff.** Develop a separately reviewed, bounded opt-in payload format and browser-camera transfer, with hash receipts. The existing LightBridge candidate is *not released* and must pass two-device optical and security tests. Camera access can require a secure context; ordinary non-HTTPS LAN URLs can be restricted.
- **C4: Two-node field link.** Manual identity and pairing approval, supervised evidence, authenticated replay protection, measured RF observations. Keep separate from the PhiPie Trail assessor.
- **C5: Housing.** Sealed inner electronics, independently qualified battery/BMS, temperature and condensation tests, external antenna, service access, safe outdoor installation.
- **C6: Installation pilot.** Written landowner/manager permission, non-damaging mounts, removal plan, ecology checks, privacy-by-default and no emergency-network promises.

We will write original code. External projects may inform requirements but should not be copied into this experiment. This prototype changes no PHIPIE-03 qualification assertions and makes no claim that PHIPIE-04 or later has completed.

**People Above Profit · Ledger Above Ego · PhiOS loves you, bro.**
