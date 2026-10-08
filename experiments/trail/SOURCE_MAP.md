# Provenance and archival source map

This PR contains the **new read-only Trail Governor code** from the rescue kit.
The original third-party-status-unverified / old-project references are described
here but intentionally are **not** checked into this public PhiPie repo.

## Input archives

- `PhiPie_Trail_Rescue_v0.1.zip` SHA-256:
  `0317ba1019a71a62b655e4b5a7f87732ab0f2adbaaee256f8ec666e797cd10e4`
- `Park_Rover_v9.0_PHI369.zip` SHA-256:
  `13c4106b7fd45b0abbf66cd182ea2431c559c9802c65003b0304707433b334aa`
- `TPO_WOS_v2_10_BG_BIGBOY_EVBridge_FULL_v2.10.4_coherence_autopilot_anchor_gate_plus.zip` SHA-256:
  `8c003973b4baaa40e1a4ca5f3abeb5adc4015de045ab3683995e841dc92334f3`
- `Bandwidth_Governor_Technical_Manual_v0_1.docx`: reviewed as a design reference,
  **not** included in this PR.

The rescue ZIP retains 23 preserved reference files with per-file SHA-256
hashes in its `PROVENANCE.json`.

## Bandwidth Governor reference inventory (in ZIP, inactive)

- `reference/tpo_bg/adapter_base.py`
- `reference/tpo_bg/adapters/unifi_stub.py`
- `reference/tpo_bg/api.py`
- `reference/tpo_bg/engine.py`
- `reference/tpo_bg/evaluator.py`
- `reference/tpo_bg/packs.py`
- `reference/tpo_bg/policy_dsl.py`
- `reference/tpo_bg/store.py`
- `reference/tpo_bg/policy_packs/common/base.yaml`
- `reference/tpo_bg/policy_packs/go/pack.yaml`
- `reference/tpo_bg/policy_packs/park/pack.yaml`

## Park Rover reference inventory (in ZIP, inactive)

- `reference/park_rover/ai/field_atlas_ledger.py`
- `reference/park_rover/ai/fleet_identity_ledger.py`
- `reference/park_rover/ai/site_deployment_ledger.py`
- `reference/park_rover/ai/steward_network_ledger.py`
- `reference/park_rover/ai/telemetry_mesh_ledger.py`
- `reference/park_rover/hardware/telemetry_mesh_ledger_v6.7.json`
- `reference/park_rover/TELEMETRY_MESH_LEDGER_v6.7.md`
- `reference/park_rover/TELEMETRY_MESH_QUICKSTART_v6.7.md`
- `reference/park_rover/STEWARD_NETWORK_LEDGER_v8.6.md`
- `reference/park_rover/STEWARD_NETWORK_QUICKSTART_v8.6.md`
- `reference/park_rover/tests/test_steward_network_ledger_v86.py`
- `reference/park_rover/tests/test_telemetry_mesh_ledger_v67.py`

Archived files have not been imported, relicensed or publicly redistributed
by this PR. A future, separately reviewed PR can propose adapted interfaces
with tests and explicit rights/security decisions.
