# ΦTrail × Φ SOMA — distributed observation contract v0.1

**Status: EXPERIMENTAL / OFFLINE / NON-QUALIFYING / UNWIRED.**  
**This is a new PhiPie-side *proposal* for SOMA organs, not a change to the
live SuperPhiVessel runtime.**

## Why this exists

SOMA, the Super PhiVessel Organ & Sensory Machine Architecture, established
an application-level distinction between sensing, interpreting, proposing,
granting and executing. Historical SOMA organ contracts included Eyes.Screen,
Eyes.Camera, Ears, Voice, Recall, Focus, Presence, Hands, Preflight and
FieldProof; Hands was locked by default, and observations were represented
with non-authorizing ObservationReceipts.

The separate SuperPhiVessel `packages/phibot-physical-observer-v0.1/` is
also intentionally *unwired*. It accepts an NBG physical-experience handoff,
not arbitrary PhiPie sensor messages.

This PR adds a **new** laboratory-only PhiPie proposal for a safe
observation seam. It does **not** automatically add organs to the Vessel UI,
send data to NBG, or grant any runtime permission.

## Proposed organs and exact allowable payloads

All listed fields are mandatory. Unknown fields are refused. No freeform
sensor object is ever accepted.

| Proposed organ | Allowlisted measurements | Excluded |
| --- | --- | --- |
| `sense.radio` | peer_id, rssi_dbm, retry_pct, sample_count | SSIDs, MACs, BSSIDs, access-point secrets |
| `sense.network` | parent_id, child_id, latency_ms, loss_pct, observed_mbps, sample_count | Packet payloads, routing commands |
| `sense.power` | battery_pct, supply_mv, cpu_temp_c | Power control commands |
| `sense.environment` | temperature_c, relative_humidity_pct | Raw audio or visual captures |
| `sense.location` | zone_id, confidence | Precise GPS coordinates and user location |
| `eyes.rover` | frame_sha256, image/jpeg, pixel dimensions, operator_once | Raw frames, continuous video, face identity |

The allowed numeric ranges, finite-number checks, and ID patterns are defined
in `trailcore/soma_observation.py`, with a matching declarative schema in
`contracts/soma-observation.v0.1.schema.json`.

`sense.network.child_id` must match the exact key-bound sender identity.
Source identity still does not prove that the sender used the indicated radio,
that a peer was reachable, or that its reported metrics were honest.

## Offline test-only authenticated intake

`SomaIntake` accepts a packet **only if all** of these hold:

1. The contract/version, required fields and strict organ payload validate.
2. The claim boundary is **exactly** non-authorizing.
3. The observation timestamp is finite, not future, and at most 90 seconds old
   (configurable and bounded).
4. The sensor's `site_id`, `node_id` and `key_id` match a *locally*
   provisioned, site/node-scoped in-memory key binding.
5. A constant-time checked HMAC-SHA256 matches the canonical JSON bytes of
   the unsigned message.
6. Its strictly increasing positive `sequence` and unique `observation_id`
   pass the same process's `ReplayWindow`. Full ledger means refusal.

The HMAC confirms possession of that particular local test key, **not**
verified sensor measurements, trusted physical hardware, authorized land
access, secure multi-hop transport, or identity attestation. We do not
implement key exchange, secure storage, rotation/revocation, or durable
anti-replay here. If a process restarts with a fresh `ReplayWindow`,
old HMAC-valid packets could be replayed. Consequently this verifier must
**not be deployed as an unattended field trust boundary**.

A trusted production design must provision hardware/device identities,
authenticate peers through an approved transport, bind keys to scoped identities,
retain atomic anti-replay state across restarts and handle clock correction,
revocation and network partition explicitly.

## Read-only receipts and no action handoff

Accepted packets produce a bounded `ObservationReceipt` carrying:

```json
{
  "contract": "phipie-trail-soma-observation-receipt/v0.1",
  "type": "ObservationReceipt",
  "authentication": "LAB_KEYRING_HMAC_ONLY",
  "somaRuntimeWired": false,
  "actionAuthorized": false,
  "authorityGranted": false,
  "mayInvokeTools": false,
  "mayIssueHardwareCommands": false,
  "safetyPlaneUnaffected": true
}
```

Other receipt fields identify observation, site, node, time, organ, sequence,
evidence SHA-256 and receipt checksum. They contain neither raw media nor
shared secrets. A receipt checksum detects later changes but does not act as
a transport signature. Sensor measurements live only in a separate in-process
advisory view; storage/access policies are still the integrator's duty.

Refused packets produce a small error code, never the suspect payload.

`soma_bridge.admit_network_link` is the *only* new path from a successfully
admitted `sense.network` packet into a `LinkObservation` for the existing
`assess_corridor`. It is **in-process only**, never a deserialized authority
token. Intermediate relay battery remains unknown until separately measured.
The governor still returns review/hold; physical motion, network writes and
deployment flags remain false.

## Intended future composed dataflow (not wired)

```text
authorized physical sensor (FUTURE)
   -> authenticated, replay-safe Infinite Porch peer (FUTURE)
   -> SOMA schema + evidence intake (OFFLINE PROTOTYPE HERE)
   -> read-only ObservationReceipt
   -> ΦTrail link/health assessment (READ-ONLY HERE)
   -> NBG epistemic episode/memory bridge (FUTURE SEPARATE REVIEW)
   -> SPV PhiBot physical observer (EXISTING, EXPERIMENTAL/UNWIRED)
   -> evidence-linked human-facing questions (FUTURE)
   X no route to Hands, motor, radio reconfiguration, or dispensing
```

This is not a substitute for the existing PhiPie hardware qualification ladder.
PHIPIE-03 remains pending physical Pi 5 evidence; a good simulated receiver
cannot complete it.

## Acceptance and reproducibility

```bash
cd experiments/trail
python -m unittest discover -s tests -v
python -m trailcore.soma_demo
```

All examples use synthetic measurements and an openly defined deterministic
**test-only** key. Never reuse this key outside the unit tests.

## Explicit gaps before field usage

- Real Wi-Fi / LoRa hardware observers and independent end-to-end link tests.
- Trusted peer and site identity, resilient clock provenance and durable replay.
- Secure remote transport, provisioned keys, key rotation and revocation.
- Consent, privacy and retention for actual camera and location observations.
- Site safety, rover e-stop/spotter and radio regulatory qualification.
- NBG memory admission and SuperPhiVessel runtime organ/receiver integration.
- Human-approved independent executors (a *different* future qualification).
- Physical field receipts, network partition and power-failure acceptance tests.

**SOMA observation != fact. HMAC receipt != permission.
Memory != command. Positive measurement != guaranteed coverage.**
