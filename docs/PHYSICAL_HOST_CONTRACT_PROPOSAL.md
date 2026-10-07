# Phi Physical Host Contract v0.1 — Proposal

Status: **non-qualifying architecture proposal**

This document defines a proposed common physical-host contract for PhiPie and future PhiBot-capable hardware.

It does **not** change the current PhiPie qualification rung, does **not** claim hardware support, and does **not** grant any new authority. PHIPIE-03 remains the active field-candidate rung.

> **Capability is not authority. Physical capability is not physical authority.**

## 1. Purpose

PhiPie already separates device identity, PhiOS identity, operator identity, PhiBot identity, model identity, and mission identity.

The next physical boundary is to separate:

- what a host can sense;
- what a host can actuate;
- what safety logic can authorize;
- what a PhiBot may recommend;
- what must remain serviceable;
- what evidence survives hardware or model replacement.

A **PhiBot-compatible physical host** is therefore not “a computer with GPIO.” It is a governed physical system with explicit identity, power, thermal, environmental, safety, service, action, and receipt boundaries.

## 2. Source design studies

This proposal synthesizes four internal PHI369 design studies as non-normative inputs:

- **EpoxyCore369** — service-bounded rugged electronics, deliberate thermal paths, sealed action interfaces, and permanent-vs-serviceable ownership.
- **PHI369 BioBattery** — deterministic protection, advisory diagnostics, local-first energy/accounting receipts, and a three-plane control split.
- **ClimateCore369** — environmental sensing, hard safety constraints, serviceable control spines, and event receipts for protective lockouts.
- **HelioVault369** — operating modes, physical interlocks, fail-safe routing, stop-build conditions, and measured safety state.

These studies inspire the contract. They do not automatically qualify any PhiPie hardware.

## 3. Core law

A physical Phi system SHOULD follow this authority chain:

```text
world / machine / environment
            │
            ▼
      sensors + inputs
            │
            ▼
deterministic safety controller
            │
            ├── hard limits
            ├── interlocks
            ├── local fail-safe
            └── emergency stop / protect state
            │
            ▼
       PhiPie host
            │
            ▼
    PhiOS governance
            │
            ▼
   PhiBot advisory layer
            │
            ▼
 proposal / explanation / mission
```

The PhiBot may diagnose, predict, summarize, prioritize, or request an action.

The deterministic safety layer retains final authority over hazardous physical behavior.

## 4. Eight physical-host planes

### 4.1 Identity Plane

Owns:

- host serial / hardware identity;
- board and carrier revision;
- secure-element identity when present;
- sensor and actuator IDs;
- firmware versions;
- serviceable-module identities.

Rules:

- device identity != PhiBot identity;
- replacement modules receive explicit identities;
- identity changes produce receipts;
- no identity implies authority by itself.

### 4.2 Power Plane

Owns:

- supply source;
- rail voltage/current;
- battery or supercapacitor state when present;
- charge/discharge state;
- fuses/contactors/protection state;
- estimated energy in, out, stored, and lost.

Rules:

- batteries and other aging/high-risk storage remain serviceable unless separately qualified;
- hard over-voltage, under-voltage, over-current, and over-temperature actions remain deterministic;
- AI may advise derating or maintenance but MUST NOT bypass hard protection;
- energy-source provenance SHOULD be recorded for field nodes.

### 4.3 Thermal Plane

Owns:

- heat-source inventory;
- temperatures and thermal sensors;
- cooling/fan state;
- heat-sink or chassis path;
- throttle/derate/protect thresholds;
- thermal qualification evidence.

Rules:

- a sealed or rugged host MUST declare where heat is expected to go;
- hot or upgradeable compute SHOULD remain serviceable unless a later qualification proves otherwise;
- thermal failure MUST have a bounded local response.

### 4.4 Environment Plane

Owns, when fitted:

- ambient temperature;
- relative humidity;
- condensation/dew risk;
- enclosure moisture/leak state;
- airflow;
- smoke/air-quality flags;
- shock/vibration/tamper state.

Rules:

- missing or stale safety-critical sensors are not treated as healthy values;
- environmental uncertainty may reduce capability;
- environmental protection events produce receipts.

### 4.5 Safety / Authority Plane

Owns:

- deterministic state machine;
- interlocks;
- emergency-stop state;
- allowlisted actuator envelopes;
- protect/derate/recovery transitions;
- operator reset requirements.

Recommended states:

```text
BOOT_SELFTEST
SAFE_IDLE
READY
ACTIVE
DERATE
PROTECT
FAULT_LATCH
RECOVERY
MAINTENANCE
```

Rules:

- probabilistic inference MUST NOT be the only authority for hazardous action;
- loss of model, network, cloud, or PhiBot MUST leave a local safe path;
- ambiguous unsafe inputs create review/protect events rather than high-risk execution.

### 4.6 Service Plane

Owns:

- permanent vs semi-permanent vs serviceable components;
- connector/service boundaries;
- module replacement procedure;
- calibration state;
- repair and inspection receipts.

Recommended ownership pattern:

```text
Permanent:
  simple MCU, identity, tamper mesh, low-power sensors

Semi-permanent:
  carrier PCB/flex, protected interconnect, shielding/ground structure

Serviceable:
  compute module, storage, radio, battery, fuse, high-wear connectors

External:
  heat sink/fins, antenna, cables, dock, labels, QR/NFC service identity
```

A design that cannot be safely serviced SHOULD NOT call permanence a reliability feature.

### 4.7 Action Plane

Owns:

- GPIO/relay/motor/pump/valve/etc. action requests;
- sealed human controls;
- actuator bounds;
- debounce / confirmation;
- command result;
- refusal reason.

Every physical action SHOULD resolve to an event contract:

```json
{
  "action_id": "uuid",
  "host_id": "phipie-node-001",
  "mission_id": "optional",
  "requested_by": "operator|phibot|system",
  "timestamp": "ISO-8601",
  "capability": "fan.set",
  "requested_value": 65,
  "authority_decision": "allow|deny|clamp|review",
  "executed_value": 65,
  "safety_state": "READY",
  "sensor_snapshot_ref": "receipt-id",
  "result": "completed|refused|fault"
}
```

### 4.8 Receipt Plane

Owns:

- sensor snapshots;
- state transitions;
- action requests and outcomes;
- energy summaries;
- thermal/environment events;
- faults;
- operator overrides;
- calibration/service history;
- module replacement;
- claim/qualification evidence.

Receipts SHOULD be local-first.

A minimal receipt SHOULD include:

```text
id
timestamp
host_id
source_plane
event_kind
state_before
state_after
inputs
decision
action
reason
operator_action
software/firmware versions
evidence refs
previous_hash
current_hash
share level
```

## 5. Three-plane control split

For safety-relevant physical hosts, PhiPie SHOULD preserve this separation:

### Plane A — Deterministic Controller

MCU-mappable hard limits, interlocks, protection transitions, and fail-safe behavior.

Plane A has physical safety authority within its declared envelope.

### Plane B — Diagnostic / PhiBot Supervisor

Pattern detection, prediction, explanation, anomaly ranking, maintenance advice, mission planning, and allowlisted requests.

Plane B is advisory unless a separate PhiOS authority decision grants a bounded action.

### Plane C — Memory / Audit

Local-first receipts, hash-chained event history, service records, energy/thermal/environment history, and exportable redacted summaries.

Plane C records authority decisions. It does not create authority.

## 6. Host manifest

A physical host SHOULD eventually expose a machine-readable manifest.

Illustrative v0.1 shape:

```yaml
contract: phi-physical-host/v0.1
host_id: phipie-node-001
platform: rpi5
profile: lab-node

planes:
  identity: present
  power: observed
  thermal: observed
  environment: optional
  safety: deterministic-local
  service: declared
  action: bounded
  receipts: local-first

compute:
  serviceable: true

battery:
  present: false
  serviceable: true

network_loss_safe: true
cloud_required_for_safety: false

authority:
  hazardous_action_requires_plane_a: true
  phibot_direct_physical_authority: false
```

This manifest is descriptive. It is not a qualification receipt.

## 7. Initial host profiles

The contract is intended to support multiple profiles without pretending they are already qualified.

### Lab Node

Bench PhiPie with sensors, safe low-voltage actions, visible receipts, and fault injection.

### Rugged Edge Node

Weather-resistant PhiPie with explicit thermal path, environmental sensing, tamper evidence, and serviceable compute/radio/power.

### Mobile PhiBot Host

Battery-backed compute with deterministic power protection, motion/actuator interlocks, environment sensing, and bounded mission authority.

### Infrastructure Controller

PhiPie supervising another system such as facility sensors, thermal equipment, network infrastructure, or a future HelioVault/ClimateCore-style controller through explicit interlocks.

## 8. Qualification boundaries

The following statements remain false until separately proven:

```text
manifest exists != hardware qualified
sensor visible != sensor trustworthy
actuator reachable != actuator authorized
PhiBot request != actuator permission
AI confidence != safety evidence
sealed enclosure != waterproof
battery telemetry != battery safety certification
one prototype pass != production qualification
local receipt != independent verification
```

## 9. Proposed future qualification ladder

This proposal does not renumber the active PhiPie roadmap.

A future physical-host ladder MAY include:

1. manifest + receipt schema;
2. safe synthetic sensor adapter;
3. deterministic safety-controller simulator;
4. low-voltage bench GPIO fixture;
5. power/thermal/environment observation;
6. fault injection and protect/recovery evidence;
7. rugged enclosure/service-boundary qualification;
8. battery-backed host qualification;
9. mobile PhiBot actuator qualification.

Each step should fail clearly and retain evidence.

## 10. Relationship to current PhiPie roadmap

This proposal does not modify PHIPIE-03 through PHIPIE-13.

The current sequence remains authoritative.

The physical-host contract becomes relevant only when a later rung deliberately adopts it or when a separate qualification track is created.

Until then, this document is an architectural bridge between PhiPie, PhiOS, PhiBots, and future governed physical systems.
