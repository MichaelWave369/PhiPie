# PhiPie runtime

This directory is reserved for PhiPie-specific node services that bridge hardware/platform concerns into PhiOS contracts.

It must not duplicate PhiOS governance logic.

Subareas:

- `node/` — node status and lifecycle;
- `identity/` — device/install pairing surfaces;
- `missions/` — bounded mission transport/execution adapters;
- `governance/` — platform enforcement adapters, not policy invention.

## Experimental physical-host simulator

`physical_host/` implements a **synthetic, non-qualifying** harness for the proposed
Phi Physical Host Contract. It contains no real GPIO or actuator driver. Its purpose
is to prove deterministic refusal/protect behavior, bounded action requests, and
local receipt chaining before physical I/O is introduced.

See [the simulator acceptance document](../docs/PHYSICAL_HOST_SIMULATOR.md).

## Physical I/O boundary

The next experimental layer is documented in
[`docs/PHYSICAL_HOST_IO_BOUNDARY.md`](../docs/PHYSICAL_HOST_IO_BOUNDARY.md).
It keeps hardware-specific sensor and actuator adapters behind deterministic
authority checks. The repository still contains no real GPIO actuator driver.
## Raspberry Pi read-only telemetry

The experimental `physical_host/pi_telemetry.py` adapter reads local Raspberry Pi/Linux host observations into receipts without becoming a Plane A safety sensor or exposing an actuator method.

See [`docs/RPI_READONLY_TELEMETRY.md`](../docs/RPI_READONLY_TELEMETRY.md).

## PhiPie health baseline

The experimental `physical_host/health_baseline.py` layer builds an explainable
local baseline from read-only Pi telemetry and reports later drift as diagnostic
evidence only. It never changes Plane A safety state and exposes no actuator
execution surface.

See [`docs/PI_HEALTH_BASELINE.md`](../docs/PI_HEALTH_BASELINE.md).

## NBG physical-memory bridge

`physical_host/nbg_memory_bridge.py` converts completed host-health episode journal records into pinned `NBG_EPISTEMIC_1` memory records. The bridge preserves inferred provenance and never grants action authority.

See [`docs/NBG_MEMORY_BRIDGE.md`](../docs/NBG_MEMORY_BRIDGE.md).
