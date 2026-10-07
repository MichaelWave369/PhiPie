# Phi Physical Host Simulator v0.1

Status: **experimental / non-qualifying**

This is the first executable slice of the proposed
[Phi Physical Host Contract](PHYSICAL_HOST_CONTRACT_PROPOSAL.md).

It intentionally uses **synthetic sensors only**. No GPIO, relay, motor, battery,
charger, pump, valve, or other physical actuator is driven by this code.

## Purpose

The simulator tests a narrow claim:

> A PhiPie-compatible physical host can preserve deterministic local safety,
> bounded action authority, and tamper-evident receipts even when a PhiBot,
> model provider, network, or cloud service is absent.

It does **not** claim that real hardware is safe or qualified.

## Implemented surfaces

- proposed host manifest validation;
- deterministic Plane A safety state machine;
- synthetic power / thermal / environment snapshots;
- derate, protect, fault-latch, recovery, and explicit re-arm behavior;
- bounded action allowlist;
- explicit separation between a PhiBot request and physical authority;
- local receipt hash chain;
- network/model-loss negative control.

## State model

```text
BOOT_SELFTEST
      │
      ▼
  SAFE_IDLE ── explicit arm ──> READY ── load enable ──> ACTIVE
      │                           │                         │
      └──────── faults ──────────┴──────── faults ────────┘
                                  │
                            DERATE / PROTECT
                                  │
                           safe snapshot
                                  ▼
                              RECOVERY
                                  │
                           explicit re-arm
                                  ▼
                                READY

Leak or E-stop:
  any eligible state -> FAULT_LATCH -> safe snapshot + operator reset -> RECOVERY
```

## Authority negative control

A PhiBot request without an external authority grant produces:

```text
authority_decision = review
executed_value = null
```

An explicit grant still does not bypass Plane A.

For example, `load.enable=true` is refused while the controller is in
`PROTECT`, even if the request says authority was granted.

The boolean grant used by this simulator is only a test seam. It is **not**
an authentication or authorization implementation.

## Synthetic scenarios

- `healthy`
- `thermal_derate`
- `thermal_protect`
- `overcurrent`
- `leak`
- `stale_sensor`
- `network_loss`
- `humid_no_airflow`

## Run locally

From the repository root:

```bash
python -m unittest discover -s tests -p "test_physical_host.py" -v
python -m runtime.physical_host.cli --scenario thermal_derate
python -m runtime.physical_host.cli --scenario network_loss
python -m runtime.physical_host.cli --scenario leak
```

The CLI emits JSON receipts followed by a summary.

## Acceptance signals

The v0.1 simulator slice passes when:

1. a healthy boot lands in `SAFE_IDLE`, not `READY`;
2. readiness requires explicit arm;
3. a PhiBot cannot directly enable the simulated load;
4. an explicit grant still cannot override `PROTECT`;
5. thermal/current thresholds produce deterministic derate/protect states;
6. leak/E-stop faults latch and require operator reset;
7. network/model loss does not disable local thermal protection;
8. receipt-chain tampering is detectable;
9. all tests pass using Python standard library only.

## What remains unqualified

```text
simulator pass != Pi hardware pass
synthetic sensor pass != calibrated sensor pass
action contract pass != GPIO safety
software interlock != independent hardware interlock
hash chain != secure hardware identity
manifest != certification
```

PHIPIE-03 remains the active PhiPie hardware field-candidate rung.
