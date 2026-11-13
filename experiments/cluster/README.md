# Φ PhiCluster + PhiPower research sandbox

**State: experimental software design, not a qualified cluster or power system.**

This isolated experiment models future PhiPie Tank / PhiGrid energy-aware
placements without touching the active PHIPIE-03 qualification work.

- The input is **synthetic**. No real power meter, BMS, solar controller, or
  PhiOS authority service is connected.
- The result is **advice**, not dispatch. No GPIO, relays, network calls,
  container runtime, image installation, or electrical controls exist here.
- A simulated permission flag does **not** authenticate any person or agent.
- Stale/future power readings, unknown/fault battery status, and critical
  battery reserve stop all proposed placements.
- Conservation mode only proposes essential jobs.
- Recommendations consume both site incremental-watt budget and node watt/slot budgets.
- Hash-linked advisory receipts are deterministic within one run, **not**
  authenticated, durable, independently attested, or PhiOS Reality Ledger events.

## Run the self-contained simulation

Requires Python 3.11+; no third-party packages.

~~~sh
python experiments/cluster/advisor.py experiments/cluster/scenario.json --now 2026-11-08T12:00:30Z
python -m unittest discover -s experiments/cluster -p 'test_*.py' -v
~~~

If you omit --now while using the checked-in dated fixture, **stale telemetry
will be refused**. That is intentional. Refreshing the fixture is a manual,
synthetic exercise, not a claim about live solar conditions.

## Contracts

Input (exact keys; unknown keys fail closed):

- schema: phicluster-synthetic/v0.1
- power: observed_at UTC Z, source=synthetic, supply_mode,
  solar_w (illustrative), battery_soc_pct, battery_health, safe_incremental_w
- nodes[]: node_id, role, state, max_incremental_w, free_slots
- jobs[]: job_id, required_role, priority, incremental_w, simulated_grant

safe_incremental_w is an **operator-supplied illustrative planning envelope
already net of the site's baseline loads and reserves**. It must never be
derived from a guessed solar rating or trusted as a BMS limit. Proposed wattage
is incremental only, not total site load or a daily energy forecast.

Output has a stable decision, refusal reason, proposed node, no-execution flag,
power mode, hash-linked dry-run receipts, and an explicit non-qualification marker.

## Milestones and boundaries

See [architecture](../../docs/PHICLUSTER_PHIPOWER_ARCHITECTURE.md) and
[starter-build field plan](../../docs/PHICLUSTER_STARTER_BUILD.md).

No PHIPIE-03/04/06/10 status has changed. Production scheduler authority,
authenticated telemetry, hardware qualification, data durability, AC transfer,
battery control, and physical deployments are **future gated work**.
