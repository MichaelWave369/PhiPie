# PHIPIE-01 — Native ARM64 Software CI

Status: **current rung**

PHIPIE-01 asks one narrow question:

> Can the PhiOS software substrate and PhiShell execute their normal software
> validation paths on a native Linux ARM64 runner without changing the PhiOS
> x86_64 release chain?

## Exact upstream input

PHIPIE-01 pins PhiOS by full commit SHA in `deps/phios.env`.

At rung creation:

```text
repository: https://github.com/MichaelWave369/PhiOS.git
commit:     dad7a7d7cd53874926ad366f19d3fc0fa6b99a49
source:     main snapshot
```

This is a software-compatibility input. It is not a claim that this commit is the
current qualified x86_64 OS image, a Raspberry Pi image, or a release candidate.

Changing the commit changes the evidence input and must be reviewed explicitly.

## Native parity matrix

The workflow runs the same pinned PhiOS source on:

| Lane | GitHub runner | Expected machine architecture | Purpose |
| --- | --- | --- | --- |
| control | `ubuntu-24.04` | `x86_64` | distinguish upstream/general failures from ARM-specific failures |
| ARM64 | `ubuntu-24.04-arm` | `aarch64` | native ARM64 compatibility evidence |

The job refuses an unexpected runtime architecture before testing.

## PhiOS core gate

Both architectures run:

- Python 3.11;
- normal PhiOS development dependencies;
- external `python-build` frontend verification;
- Ruff;
- Mypy;
- the full `pytest -q` suite;
- the no-telemetry policy;
- wheel construction;
- installation into a clean virtual environment;
- installed-package import and CLI-help smoke checks.

The ARM64 lane therefore tests the same core contract suite rather than a reduced
"it imported once" subset.

## PhiShell gate

Both architectures run the upstream PhiShell validation path:

- Node 22;
- dependency installation;
- contract tests;
- Linux host probe;
- allowlisted systemd service probe;
- process/package/device probes;
- coherent system-state composition;
- bounded change derivation;
- TypeScript/Vite build;
- same-origin transport check.

This is Linux userspace evidence. It is not Raspberry Pi graphics or hardware evidence.

## ARM64 native backend gate

The ARM64 runner additionally installs and exercises the optional native backends used by
governed memory and ledger reporting:

- `sqlite-vec==0.1.9`;
- `duckdb==1.5.5`;
- Bubblewrap isolation;
- governed-memory vector tests;
- ledger report / DuckDB tests.

This is intentionally a required lane. A missing ARM64 binary dependency should fail the
rung rather than disappear behind `continue-on-error`.

## PHIPIE-01 completion rule

PHIPIE-01 is complete only when the aggregate `PHIPIE-01 gate` is green for the exact
PhiPie commit being merged.

A green rung supports the bounded statement:

> The pinned PhiOS software stack and PhiShell passed the PHIPIE-01 native ARM64
> software validation protocol on the GitHub-hosted ARM64 Linux environment.

It does **not** establish:

- a bootable PhiPie image;
- Raspberry Pi 5 or Compute Module 5 boot support;
- Pi firmware/device-tree correctness;
- GPU/DRM/Wayland hardware behavior;
- HDMI, USB, Ethernet, Wi-Fi, Bluetooth, GPIO or NVMe support on a Pi;
- thermal or power behavior;
- physical-device persistence;
- secure boot;
- production qualification.

Those belong to later rungs.
