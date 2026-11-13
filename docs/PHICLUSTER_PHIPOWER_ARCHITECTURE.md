# Φ PhiCluster / PhiPower — design v0.1

**Status: architecture proposal and isolated synthetic software experiment.**
Owner: PhiPie ARM64 platform repo. PhiOS remains owner of governance, applications,
identity, mission authority and ledger. This design does not modify PhiOS or
the qualified x86_64 release chain.

## Why

Provide resilient, local-first services using small, repairable compute nodes
with energy-aware advisory scheduling. Lower recurring power needs by keeping
a modest always-on substrate separate from optional high-power GPU work.

The hardware milestone is **still PHIPIE-03 (real Pi 5 boot evidence)**.
PHIPIE-04 runtime, PHIPIE-06 headless mode and PHIPIE-10 multi-role Tank are
not qualified or unblocked by these documents or simulation.

## Layered concept

~~~text
Human owner / PhiOS UI / explicit policy (later)
                    |
            PhiGrid / PhiCluster
   observer + planner + local receipts (experimental)
                    |
     +--------------+--------------+
     |              |              |
 PhiPie Control  PhiPie Service  PhiPie Vault
 Pi 5 candidate  Pi 5 candidate  Pi 5 candidate
   health/UI        apps/jobs      backups
     +--------------+--------------+
          private local network
                    |
         PhiPower telemetry plane
 PV --> certified charge equipment --> protected LiFePO4 --> fused DC
                    |
       deterministic local protection
~~~

The PhiPower plane is observed only by the cluster planner. All battery
protection, overload/undervoltage limits, AC transfer and disconnects belong
to properly rated deterministic hardware, not to a Python scheduler, PhiBot,
or model. PhiPie power advice never authorizes hazardous physical action.

## Node identity and roles

- **Control**: dashboard, status collector, owner-approved configuration and
  advisory scheduling, never a single unreplaceable authority.
- **Service**: small local-first services, Commonline/PhIRCQ adapters,
  PocketBrain-class inference if benchmarks justify it.
- **Vault**: encrypted SSD/NVMe and independently recoverable backups,
  not a sole copy of critical files.
- Future opt-in roles: mesh, sense, agent, xr-link. Role capability is never
  equivalent to trust or permission.

Explicit identities remain distinct: device != PhiOS installation !=
operator != PhiBot != model provider != mission. CM5 requires its own
qualification; one Pi 5 passing does not qualify a three-node cluster.

## Energy policy, not power control

The planner accepts operator-declared *incremental* power budgets as inputs,
along with synthetic battery SOC/health and the age of observations.

- **normal** at SOC >= 45% and valid battery telemetry: eligible jobs can
  be proposed within each node's slots/watts and overall watts.
- **conservation** at 20% <= SOC < 45%: essential proposals only.
- **critical** below 20%: no new job proposals.
- **untrusted** for stale, future-dated, faulty/unknown battery telemetry or unknown supply mode:
  no new job proposals.
- Jobs without a synthetic grant are denied, but this toy boolean is not
  actual authentication or a PhiOS grant.
- All v0.1 output is simulation-only; no process dispatch, GPIO, relays,
  battery actions, networking, or inference-driven switching.

These are **software demonstration thresholds**, not safe lithium battery
cutoffs or recommended battery BMS configuration. Hardware thresholds require
battery-manufacturer specifications, measured load tests and qualified
protective components. Reserve for cooling, router, controls and converter
losses must be included **before** supplying a budget. A stale reading does
not mean existing workloads have been shut off. The prototype is not wired
to do that.

## Governance, privacy and availability

- Private LAN first; no unsolicited public service exposure.
- Authentication, per-node keys, operator approval and signed telemetry are
  required before any future real deployment; never equate reachability with trust.
- A future PhiOS grant must be evaluated on the target as well as coordinator.
- Physical safety is independent of network, cloud and model availability.
- Pause/kill capabilities must have owner-controlled, locally reachable paths.
- Receipts should be local-first and tamper-evident, with eventual PhiOS ledger
  integration; the demo hash chain proves only in-process deterministic linkage.
- Privacy-first status collection; no cameras or identifying telemetry by default.
- Vault backups must be encrypted, restorable and periodically tested;
  a single Vault node is not a backup strategy by itself.
- Planner failure has no physical side effects; do not implement unattended
  transfer switching or auto-wake of large machines in the sandbox.

## Future interface contracts (not live)

1. **Observation**: sensor ID, sampled_at UTC, provenance, measurement units,
   fault/stale status, signed authenticity, age and quality.
2. **Node profile**: independent device ID, image hash, role, measured
   incremental watts at load, temperatures, storage, status and limits.
3. **Job envelope**: bounded resources, network/filesystem scope, mission ID,
   authenticated authority reference, priority, expected energy and deadline.
4. **Policy decision**: allowed/defer/deny, budget, reason, evidence references.
5. **Receipt**: request/decision/action separation, previous hash,
   software/image/host provenance and redaction level.
6. **Physical boundary**: deterministic safety MCU/BMS before any approved
   low-voltage fixture; no PhiBot-direct battery switching.

## Energy-sizing worksheet (illustrative ONLY)

Illustrative baseline: three tiny nodes averaging 8 W each plus 5 W for
networking = 29 W continuous **assumption**, not a Pi 5 measurement.

- DC loads: 29 W * 24 h = 696 Wh/day.
- With assumed end-to-end 85% delivery efficiency: 696 / 0.85 =
  about **819 Wh/day** drawn from storage/generation.
- Hypothetical 400 W PV * 3.5 equivalent sun hours * 0.75 performance
  factor = **1,050 Wh/day**, highly seasonal/site/shading dependent.
- Hypothetical 25.6 V * 100 Ah LiFePO4 = 2,560 Wh nominal.
  At 80% allowed usable fraction * 90% delivery efficiency, roughly
  **1,843 Wh usable**, ~2.25 no-sun days at the illustrative 819 Wh/day.

Do not size purchased equipment from these assumptions. Measure real wattage
at idle, boot, peak load, networking, cooling and charging; use local worst-
month solar data, autonomy targets, component datasheets and competent
electrical design. PV nameplate watts are not measured generation; battery
capacity is not necessarily usable energy.

## Hardware safety constraints

- Start with prebuilt, listed/certified solar charge equipment, battery
  packs/BMS and DC-DC supplies rated for actual loads.
- Correct fuses, wiring ampacity, disconnects, moisture protection,
  strain relief, thermal control and polarity protection are mandatory.
- Respect LiFePO4 low-temperature charging restrictions and manufacturer
  voltage limits; do not DIY cell-level protection.
- Do not connect a prototype inverter to RV/house branch circuits or the
  utility grid; any permitted transfer/shore-power integration needs a
  qualified electrician and code-compliant design.
- Outdoor/tree-mounted Canopy or waterproof lunchbox enclosure ideas are
  unqualified until thermal, water ingress, wildfire and mounting risks
  have been tested. Do not seal actively cooled boards without a heat path.

## Evidence ladder

- C0: docs and pure synthetic advisor, 100% no-action output (this PR).
- C1: one real metered Pi 5 bench node, separate from PHIPIE-03 qualification.
- C2: three nodes on an isolated LAN with measured power, faults and recovery.
- C3: read-only, authenticated solar/BMS telemetry; monitor only.
- C4: explicit owner-approved workload execution, sandboxing, rollback and
  durable audit; separate review and qualification.
- C5: protected battery/solar hardware integration only after physical design,
  electrical inspection, safety analysis and extensive fault testing.

No stage implies the next one, nor automatically advances the PhiPie roadmap.
