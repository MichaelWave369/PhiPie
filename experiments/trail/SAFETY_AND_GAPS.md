# ΦTrail v0.1 safety and gaps

## Supported

- Deterministic evaluation of provided directed-link telemetry.
- Conservative rejection of missing, stale, duplicate, nonfinite and otherwise
  out-of-bounds measurements.
- Human/site permission **assertions** included in review requirements.
- Read-only Park Rover v6.7 health packet parsing with a non-authenticating hash.
- Explicit refusal flags for physical deployment, motor motion, network changes,
  and end-to-end identity/reachability proof.

## Not supported / not qualified

1. **No actual RF transport:** no Wi-Fi mesh, LoRa, point-to-point, Starlink,
   AP provisioning, routing or channel selection implementation.
2. **No verified end-to-end bandwidth:** per-link minimum throughput and hop
   latency sum are diagnostic proxies, not an end-to-end measurement.
3. **No cryptographic identity:** checksums detect changes, not spoofing,
   malicious fabrication, or replay attacks.
4. **No real access control:** permission mappings are inputs from the caller,
   not signed approval, scoped operator identity or verified land authorization.
5. **No network changes:** TPO BG's legacy UniFi adapter is a simulator;
   action verification/rollback and authorization boundaries need repair.
6. **No autonomous rover:** Park Rover beacon states cannot grant drive,
   dispense, recovery or any other physical authority.
7. **No physical qualification:** battery, environment, RF interference,
   durability, thermal and weather limitations are untested on hardware.
8. **No emergency guarantee:** no measured range, reliability, redundancy,
   uptime, regulatory compliance, or life-safety certification.

## Mandatory future controls

- Default read-only; require independently verified device/operator/site
  identity and signed anti-replay receipts before trusted field decisions.
- Preserve independent physical stop, preflight, geofencing, landowner
  permission, human spotter and rover safety controller.
- Separate control plane from user traffic; limit admin exposure; encrypt
 /authenticate the link, protect keys and prohibit secret logging.
- Future network policy writes need whitelist, bounded scope, rollback,
  rate limits, observability and explicit authenticated approval.
- No unsanctioned installations, hidden tracking, ecosystem disturbance
  or abandoned electronics in forests, parks or campgrounds.

## Legacy source boundary

The original TPO BG API and engine have authorization/verification gaps;
the original UniFi adapter fabricates telemetry and simulates writes.
They must not be imported as executable production dependencies. Keep
license review and full security review before any public source vendoring.

PhiPie PHIPIE-03 status and existing CI are not modified by this experiment.

## Linux observer follow-on (experimental, PR #14)

`RADIO_OBSERVER.md` describes optional read-only Linux `iw` link/driver
queries and bounded, explicitly operator-approved ICMP packets on a
private network. No radio or router writes are permitted. These measurements
remain locally observed/unattested, and missing or unsupported driver
statistics block SOMA packet drafting. No field radio/routed-mesh claims.

## Two-node lab handoff limits (PR #15)

See [TWO_NODE_PILOT.md](TWO_NODE_PILOT.md).
The pilot's HMAC proves a shared lab key was used, not secure peer/device
identity or accurate physical measurements. Its durable SQLite replay ledger
handles normal restarts but cannot stop rollback/replacement of the disk.
No built-in transport exists. Payload exchange needs independently secured
manual transfer, permission to observe, current clocks and protected secrets.
Positive receipt is never permission to change radio configuration or drive.
