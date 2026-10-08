# ΦTrail: PhiPie Trail Governor v0.1

**Status: EXPERIMENTAL / OFFLINE ADVISORY ONLY / NO HARDWARE CONTROL**

ΦTrail is a standalone, standard-library Python proof of concept for reviewing an ordered
gateway → PhiPie relay(s) → Park Rover corridor. It comes from the
`PhiPie_Trail_Rescue_v0.1.zip` rescue exercise and does not change PhiPie image building,
the PhiOS runtime, any Pi radio, or Park Rover's safety controller.

> Capability is not authority. Healthy telemetry never permits deployment, driving,
> router changes, or claims of emergency communications coverage.

## Try it (Python 3.10+)

```bash
cd experiments/trail
python -m trailcore.demo nominal
python -m trailcore.demo degraded
python -m trailcore.demo stale
python -m unittest discover -s tests -v
```

Expected states: `nominal → REVIEW_CANDIDATE`; `degraded/stale → HOLD`.
Even the nominal result is **human review**, not authorization.
Example metrics are synthetic and represent no actual field measurements.

## What is included

- `trailcore/governor.py`: deterministic assessment of ordered links, missing/duplicate
  observations, freshness, latency, loss, throughput, relay battery, and operator/site
  permission assertions. Always returns hardware and network authority flags as false.
- `trailcore/rover_bridge.py`: defensive normalization of a Park Rover v6.7 health
  beacon's age, shape, safety claims and checksum. A checksum is **not authentication**.
- `trailcore/demo.py`: three completely synthetic, reproducible scenarios.
- `tests/`: offline invalid data, stale telemetry, tampering, permission, topology,
  no-actuation and source-boundary checks.
- `ARCHITECTURE.md`, `FIELD_VALIDATION.md`, `SAFETY_AND_GAPS.md`: extraction,
  hardware qualification plan and reasons this remains advisory.
- `SOURCE_MAP.md`: source archive provenance and the code intentionally **not** imported.

## Why the reference sources are not blindly vendored

The rescue ZIP contains 23 original TPO/Bandwidth Governor and Park Rover reference
files. The source set includes an unverified UniFi stub, unsafe legacy API paths and
legacy license provenance requiring review. Those archival files remain in the
original rescue ZIP rather than silently becoming active production code in this
public MIT repository. The **new** advisory module and its tests are included here.

To inspect or integrate the archived references, use the original local
`PhiPie_Trail_Rescue_v0.1.zip`, verify its SHA-256 listed in `SOURCE_MAP.md`, and
review licensing, authentication, authorization and rollback separately.

## No unsupported claims

This package does **not** implement a routed Wi-Fi mesh, a LoRa transport, validated
Starlink backhaul, Infinite Porch peer integration, authenticated evidence, AI routing
control, a rover dispenser, autonomous movement, emergency coverage, or link-health
measurements from a physical device. Sum of hop latencies / minimum hop throughput
are diagnostic proxies, **not measured end-to-end performance**.

This is an **optional experiment**, not a new qualification rung. PHIPIE-03 remains
a field candidate until qualified on real Raspberry Pi 5 hardware. Nothing here
changes the existing PhiPie roadmap or claims.

## ΦTrail × Φ SOMA v0.1 (read-only experiment)

The [distributed SOMA observation proposal](SOMA_DISTRIBUTED.md) adds strict
`sense.radio`, `sense.network`, `sense.power`, `sense.environment`,
`sense.location`, and `eyes.rover` contracts; bounded ObservationReceipts;
an offline HMAC lab verifier with process-local replay refusal; and a one-way
network-observation adapter into Trail Governor.

Run `python -m trailcore.soma_demo` from this directory to see the synthetic
signed observation become an advisory corridor review. This is not a live
SuperPhiVessel SOMA integration, nor a qualified radio observer, physical network,
secure field identity system, or permission to actuate.

## Physical read-only Linux radio observer v0.1

[PR #14 radio observer](RADIO_OBSERVER.md) adds a real Linux `iw`-based
interface/link/counter observer, strict missing-data handling, and optional
operator-approved **bounded private-IP ICMP** probes. An `sense.radio` SOMA
message is emitted only as an **unsigned draft** if complete passive evidence
is available; it does not create trusted credentials or push observations into
live SuperPhiVessel. GitHub CI exercises fake command outputs, not hardware.

## Two-node signed radio evidence pilot v0.1

The [two-node evidence pilot](TWO_NODE_PILOT.md) explicitly provisions a
**lab-only symmetric key**, creates owner-only signed radio-evidence files
on the sender, and verifies them on a receiver using a SQLite replay ledger
that survives normal process restarts. **Transfer is manual and external.**
No network daemon, live Porch/SOMA wiring, or Pi hardware qualification
is introduced. This is a small laboratory step toward a two-PhiPie field trial.

## Supervised two-node field evidence review kit v0.1

The [ΦTrail Field Witness Kit](FIELD_WITNESS.md) adds a privacy-minimized,
read-only Linux host snapshot and strict two-Pi operator evidence assessment.
It is a **manual test checklist and validator**, not physical qualification,
live mesh deployment, or a security attestation. No existing software
qualification status or runtime authority changes.

## Private evidence binding v0.1

The [local evidence binder](EVIDENCE_BINDING.md) checks seven protected
host/radio/packet/receipt/path JSON files against the operator's #16
field-witness hash references. It refuses missing, tampered and unsafe
files and emits only file-consistency status, **not proof that hardware
actually ran the tests**. It performs no network activity or HMAC key exchange.
