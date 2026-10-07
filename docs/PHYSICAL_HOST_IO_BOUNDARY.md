# Phi Physical Host I/O Boundary v0.1

Status: **experimental / non-qualifying**

This slice follows the synthetic physical-host simulator and adds the boundary
that future real sensor and actuator drivers must cross.

No real GPIO or physical actuator driver is included.

## Core rule

```text
PhiBot / operator / system request
             │
             ▼
      deterministic Plane A
             │
      ┌──────┴──────┐
      │             │
 REVIEW / DENY   ALLOW / CLAMP
      │             │
      ▼             ▼
 no adapter      actuator adapter
 invocation          │
                     ▼
              execution receipt
```

A request that is reviewed or denied never reaches the actuator adapter.

An allowed request may reach the adapter, but adapter failure immediately
produces a local `PROTECT` transition and a receipt.

## Why this exists

Real GPIO libraries, relay boards, motor controllers, pumps, battery interfaces,
and other hardware should not be imported directly into PhiBot or mission code.

Future hardware-specific integrations should implement the small adapter
contracts in `runtime/physical_host/io.py`.

That preserves:

- deterministic authority before physical I/O;
- a single auditable crossing point;
- simulator parity;
- replaceable hardware drivers;
- explicit failure behavior.

## Added contracts

Two draft JSON Schema documents are included:

- `contracts/physical_host/manifest-v0.1.schema.json`
- `contracts/physical_host/receipt-v0.1.schema.json`

The repository does not claim full JSON Schema qualification yet. The tests
verify that the canonical manifest and generated receipts carry the required
contract fields using Python standard library only.

## Negative controls

CI proves that:

1. a PhiBot request in `REVIEW` causes zero actuator calls;
2. a denied request causes zero actuator calls;
3. a clamped action passes only the bounded value;
4. an actuator-adapter failure forces `PROTECT`;
5. the receipt chain remains valid across execution failure.

## Boundary

```text
adapter interface != GPIO qualification
recording sink != actuator hardware
JSON schema != certification
ALLOW decision != proof a connected device is safe
software PROTECT != independent hardware interlock
```

PHIPIE-03 remains the active Raspberry Pi 5 hardware field-candidate rung.
