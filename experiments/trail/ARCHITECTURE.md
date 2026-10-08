# Trail rescue architecture and separation of authority

```text
[Starlink / other authorized uplink]
          |
 [Gateway / trusted router]   (NOT implemented in this module)
          |
 [PhiPie relay 1] --- [PhiPie relay 2] --- [Rover/PhiPie]
       |                     |                  |
  measurements         measurements      health beacon
       +---------------------+------------------+
                             |
                   [Trail Governor]
                     ADVISORY ONLY
                             |
                    REVIEW / HOLD
                             |
                     Human operator
              independent field qualification
```

## What is real in this PR

The deterministic `assess_corridor` function consumes **caller-supplied** observations
with explicit directed parent and child node IDs. For each required hop it checks
finiteness, age, sample count, measured (but not attested) RTT/loss/throughput, and
intermediate relay battery. Inputs supply operator presence and site permission
*assertions*; the function does **not** authenticate these assertions.

The Park Rover bridge accepts a v6.7 `telemetry_mesh_packet`, checks packet shape,
timestamp and SHA-256 and carries only `last_decision.state` and a no-motion claim.
SHA-256 does not identify the sender. A replayed or fabricated checksum-valid
packet can still be untrusted.

Positive status means **REVIEW_CANDIDATE**. Missing, stale or malformed evidence
means **HOLD**. All returned authority flags remain false by construction.

## Rescued designs to adapt later, not imported here

**TPO / Bandwidth Governor:** policy DSL, evaluator, adapters, groups, telemetry
rollups, incidents, logs and verify/rollback concepts. Its UniFi adapter is
synthetic and its legacy API/engine need security and verification repairs.

**Park Rover v9.0:** telemetry beacon ledger, steward/site/fleet identity
evidence and field atlas. Rover `Telemetry Mesh` is health telemetry, not
a proven P2P radio mesh or authorization to move.

**Infinite Porch:** a future authenticated peer / communications substrate.
No transport or cryptographic proof is assumed by this experiment.

**BrainC / NBG:** future *advisory* placement history, not an authority source.

**PhiPie / PhiOS:** platform provisioning and governance are separate; the
Raspberry Pi 5 physical qualification rung remains unchanged.

## Proposed future contracts (unimplemented)

- `PhiPieRadioObserver`: read-only interface to actual Pi radio RSSI,
  retry/airtime, neighbor identity, path packet loss, timing and throughput
  with known provenance.
- `TrustedTopologyLedger`: authorized site, surveyed nodes and signed/verified
  survey receipts; replay prevention and bounded freshness.
- `TrailPolicyAdvisor`: proposes rate tiers during congestion and produces
  an auditable dry-run only; it never writes live AP settings.
- `HumanApprovedExecutor`: separate future service requiring authenticated
  human approval, platform capability proofs, verify and rollback.
- `RoverSafetySpine`: independent motion authority, physical stop, preflight
  and spotter; cannot be bypassed by network intelligence.

The first real integration must be **observation-only**.
