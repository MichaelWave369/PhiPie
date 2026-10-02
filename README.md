# Φ PhiPie

**A tiny, governed PhiOS node for real-world computation.**

PhiPie is the ARM64 hardware platform for the [PhiOS](https://github.com/MichaelWave369/PhiOS) ecosystem. Its purpose is to bring the same authority-aware computing model used by PhiOS onto Raspberry Pi-class hardware for desktop, headless edge-node, agent-runtime, and future cluster deployments.

> **Capability is not authority.**

PhiPie is **not** a fork of PhiOS. PhiOS owns the operating-system contracts, governance model, memory, ledger, application platform, shell, and agent interfaces. PhiPie owns the hardware distribution layer needed to run those capabilities on ARM64 devices.

## Status

**PHIPIE-03 — Raspberry Pi 5 field candidate**

PHIPIE-00 established the platform contract. PHIPIE-01 proved the pinned PhiOS software stack on native ARM64 CI. PHIPIE-02 produced the first Pi 5-targeted ARM64 disk image with provenance.

PHIPIE-03 now prepares a dedicated physical-test image that captures bounded first-boot evidence on a real Raspberry Pi 5. CI can qualify the field candidate, but **only a real board can complete PHIPIE-03**.

The PhiOS runtime is intentionally still not installed in this rung. That integration remains PHIPIE-04.

See [PHIPIE-03](docs/PHIPIE_03_RPI5_BOOT_QUALIFICATION.md) and the [roadmap](docs/ROADMAP.md).

## Intended platform path

```text
PhiOS Core
   │
   ├── x86_64 distribution
   │      └── desktop / VM / physical PC
   │
   └── ARM64 distribution
          └── PhiPie
               ├── Raspberry Pi 5 development target
               ├── Compute Module 5 appliance target
               └── future multi-node PhiPie Tank
```

## Design rules

```text
PhiPie != PhiOS fork

ARM64 build success != hardware qualification
image constructed != image booted
field receipt != hardware qualification
installed != authorized
network reachable != trusted
device identity != PhiBot identity
model provider != agent identity
capability != authority
```

## Planned modes

- **PhiPie Desktop** — human + Vessie workstation with PhiShell and local applications.
- **PhiPie Node** — headless governed agent/edge node with remote inspection and mission execution.
- **PhiPie Tank** — multiple governed nodes used as a physical Think Tank substrate.

## License

MIT. See [LICENSE](LICENSE).

**Plug In → Govern → Create.**
