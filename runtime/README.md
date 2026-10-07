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
