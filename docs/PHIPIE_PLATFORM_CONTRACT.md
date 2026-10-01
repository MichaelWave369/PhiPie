# PhiPie Platform Contract — PHIPIE-00

Status: **draft platform contract**

PhiPie is the ARM64 hardware distribution layer for the PhiOS ecosystem.

## 1. Ownership boundary

PhiOS owns:

- authority and governance contracts;
- Reality Ledger and evidence semantics;
- governed memory;
- application lifecycle;
- PhiShell and MCP-facing interfaces;
- Covenant identity/recovery contracts;
- agent-facing authority boundaries.

PhiPie owns:

- ARM64 image composition;
- Raspberry Pi-family hardware profiles;
- platform-specific boot, firmware, device, graphics, networking and storage integration;
- node-local service packaging;
- hardware qualification evidence;
- future provisioning and update packaging specific to PhiPie.

PhiPie **consumes PhiOS**. It does not fork PhiOS core.

## 2. Architecture boundary

```text
PhiOS contracts / runtime / apps
            │
            ▼
PhiPie integration layer
            │
            ▼
ARM64 Linux userspace
            │
            ▼
Pi-family kernel / firmware / boot
            │
            ▼
physical hardware
```

A lower-layer capability never silently grants an upper-layer authority.

## 3. Initial targets

The initial development target is Raspberry Pi 5.

Compute Module 5 is a later, independently qualified appliance target.

A future PhiPie Tank may compose multiple qualified nodes, but cluster behavior is not implied by single-node success.

## 4. Operating modes

### PhiPie Desktop

A display-attached human + agent workstation.

### PhiPie Node

A headless governed execution node with remote observation/control through explicit PhiOS interfaces.

The two modes may share an image family, but their enabled services and authority profiles may differ.

## 5. Identity separation

```text
physical device identity
!=
PhiOS installation identity
!=
operator identity
!=
PhiBot identity
!=
model/provider identity
!=
mission identity
```

Each relation must be explicit and auditable.

## 6. Qualification laws

```text
build success != boot success
boot success != device support
device support != desktop support
desktop support != node support
one-board pass != model-family qualification
Pi 5 pass != CM5 pass
installed != authorized
reachable != trusted
capability != authority
```

## 7. PHIPIE-00 exit criteria

PHIPIE-00 is complete when the repository contains:

- this platform contract;
- architecture and qualification documents;
- a rung-based roadmap;
- directory ownership notes;
- a structural CI check.

No boot image is required for PHIPIE-00.
