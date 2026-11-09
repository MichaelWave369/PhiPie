# Φ PhiPie three-node starter / field-readiness plan

**Blueprint, not a wiring diagram or bill of materials.**

## Roles to demonstrate

| Node | Candidate platform | Work to prove | Stop condition |
| --- | --- | --- | --- |
| pie-control-01 | Pi 5, active cooled, NVMe | local status, health, owner UI | loss of local control / unexplained boot fault |
| pie-service-01 | Pi 5, active cooled, NVMe | bounded local apps and synthetic jobs | unstable thermals / denied authority |
| pie-vault-01 | Pi 5 + serviceable storage | tested encrypted restore / backup receipts | any unverified restore or silent corruption |

Pi 5 is the initial research target. CM5 is separate. A candidate image
is NOT an installed and qualified PhiOS node; PHIPIE-03 evidence remains
required before a subsequent PhiOS integration rung.

## Bench-first commissioning sequence

1. **Measure**, before buying solar: use an appropriate power meter to record
   each board's idle, boot surge, sustained CPU, NVMe and network draw.
   Log cooling, ambient temperature, failure and recovery behavior.
2. **Network**, with existing trusted LAN and individual node keys once a
   real governed runtime exists; no port forwarding or default remote root.
3. **Simulate**: run experiments/cluster/advisor.py and its negative tests.
   Confirm stale telemetry and faults block new job proposals.
4. **Budget**: add measured network/switch and converter losses; choose a
   target reserve/autonomy and perform worst-month solar calculations.
5. **Power**: bench each node with manufacturer-supported stable USB-C/DC
   supplies. Only later consider a professionally designed, fused DC
   distribution system and certified charge controller/BMS combination.
6. **Prove resilience**: disconnect one noncritical node, reboot, restore
   from encrypted backup and verify receipts without an external cloud.
7. **Integrate** real PhiOS authority, metering and work execution only as
   separate gated proposals. Never allow the planning demo to actuate
   electrical equipment.

## What to capture for each actual board

- Exact Pi board model/revision; Pi 5 != CM5; image and commit hashes.
- Firmware/kernel versions, power supply rating, actual bus voltages.
- Measured W at idle, peak and boot; ambient/board temperature; cooling.
- Network loss, local access, recovery, storage durability and evidence logs.
- Explicit operator approval and tested rollback; fault cases retained.
- Calibration, BMS/controller model and safe envelope for later power tests.

## Go/no-go

**Go:** synthetic advisor tests pass; isolated plan-only outputs; an
owner-reviewed separate bench plan; verified hardware power measurements.

**No-go:** unknown battery BMS behavior; unprotected battery wiring; stale
telemetry treated as safe; any relay/AC control from an AI decision; claims
that CI passing proves off-grid operation; tree/canopy deployment without
weather/fire/thermal qualification.

Keep the expensive GPU host optional and manually controlled until this
low-power baseline is real and repeatable.
