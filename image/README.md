# Image system

This directory owns PhiPie image composition.

PHIPIE-02 activates the first image builder using an exact pinned Raspberry Pi
`rpi-image-gen` source commit.

Current paths:

- `configs/` — image/profile configuration;
- `hooks/` — minimal build-time filesystem customisation;
- `layers/` — reserved for PhiPie composable layers as the image grows;
- `overlays/` — reserved filesystem/config overlays;
- `packages/` — reserved PhiPie-specific packaging metadata.

The PHIPIE-02 profile intentionally does not install PhiOS yet. It proves image
construction before PHIPIE-03 physical boot evidence and PHIPIE-04 PhiOS runtime
integration.
