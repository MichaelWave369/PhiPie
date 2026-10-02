# PHIPIE-02 — Minimal ARM64 image builder

Status: **current rung**

PHIPIE-02 turns the ARM64 software evidence from PHIPIE-01 into an actual Raspberry Pi
5-targeted disk-image artifact while keeping physical hardware claims at zero.

## Builder

The image toolchain is Raspberry Pi's `rpi-image-gen`, pinned by exact commit in
`deps/rpi-image-gen.env`.

Pinned builder input:

```text
repository: https://github.com/raspberrypi/rpi-image-gen.git
commit:     6fec7d5ed1a1c68a6bcab8af74603ae1355d7916
source:     master snapshot
```

The fetch helper refuses branch drift, a non-exact SHA, or an unexpected repository.

## Image profile

`image/configs/phipie-rpi5-min.yaml` deliberately stays small:

- Raspberry Pi 5 device layer;
- Raspberry Pi OS-style image layout;
- Debian Trixie `trixie-minbase` suite;
- hostname `phipie`;
- fixed `SOURCE_DATE_EPOCH`;
- PhiPie image marker written into `/etc/phipie-release`.

The PhiOS runtime is **not installed in this rung**. PHIPIE-04 owns that integration.

## CI construction

The required image lane runs on GitHub's native ARM64 runner and follows the same
host family used by upstream `rpi-image-gen` CI:

1. prove the runner is ARM64;
2. fetch the exact builder commit;
3. install the builder's declared dependencies;
4. build the minimal Pi 5 image;
5. verify the image is non-empty and has boot-style plus Linux partitions;
6. calculate the raw image SHA-256;
7. emit `phipie.image-manifest.v1`;
8. compress the image with zstd;
9. publish the compressed image, hashes, partition report and manifest as the CI artifact.

## Reproducibility boundary

PHIPIE-02 pins:

- PhiPie source identity;
- PhiOS input identity carried forward from PHIPIE-01;
- rpi-image-gen source identity;
- image configuration;
- `SOURCE_DATE_EPOCH`;
- the produced image digest.

However, the initial profile uses the normal `trixie-minbase` suite. Package repositories
can advance independently of this repository. Therefore **PHIPIE-02 does not claim that
a future rebuild will be bit-for-bit identical** merely because the source commits match.

The first artifact is reproducibly *specified and attributable*, not yet proven
bit-identical across repository time. A later hardening rung can snapshot every package
source before such a claim is made.

## Exit claim

A green PHIPIE-02 gate supports only:

> The exact PhiPie source and pinned rpi-image-gen toolchain successfully constructed
> a Raspberry Pi 5-targeted ARM64 disk image, and that artifact's identity and partition
> structure were recorded.

It does not prove the image boots on a Raspberry Pi 5.

That is PHIPIE-03.
