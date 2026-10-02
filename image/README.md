# Image system

This directory owns PhiPie image composition.

The image builder is Raspberry Pi's `rpi-image-gen`, pinned by exact source identity.

Current profiles:

- `configs/phipie-rpi5-min.yaml` — PHIPIE-02 minimal construction image;
- `configs/phipie-rpi5-field.yaml` — PHIPIE-03 physical boot field candidate.

Current support paths:

- `configs/` — image/profile configuration;
- `hooks/` — build-time filesystem customisation;
- `field/` — observation-only first-boot collector embedded in the field image;
- `layers/` — reserved for PhiPie composable layers as the image grows;
- `overlays/` — reserved filesystem/config overlays;
- `packages/` — reserved PhiPie-specific packaging metadata.

Neither current profile installs the PhiOS runtime. PHIPIE-04 owns that integration.
