# Φ PhiPie

**A tiny, governed PhiOS node for real-world computation.**

PhiPie is the ARM64 hardware platform for the [PhiOS](https://github.com/MichaelWave369/PhiOS) ecosystem. Its purpose is to bring the same authority-aware computing model used by PhiOS onto Raspberry Pi-class hardware for desktop, headless edge-node, agent-runtime, and future cluster deployments.

> **Capability is not authority.**

PhiPie is **not** a fork of PhiOS. PhiOS owns the operating-system contracts, governance model, memory, ledger, application platform, shell, and agent interfaces. PhiPie owns the hardware distribution layer needed to run those capabilities on ARM64 devices.

## Status

**PHIPIE-01 — native ARM64 software compatibility CI**

PHIPIE-00 established the platform contract and repository boundaries. PHIPIE-01 now tests an exact pinned PhiOS source on native x86_64 and native ARM64 Linux runners, including PhiOS core, PhiShell, and the ARM64 native memory/ledger backends.

No production PhiPie image exists yet. No Raspberry Pi or Compute Module hardware is qualified by this repository yet.

See [PHIPIE-01](docs/PHIPIE_01_ARM64_SOFTWARE_CI.md) and the [roadmap](docs/ROADMAP.md).

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
