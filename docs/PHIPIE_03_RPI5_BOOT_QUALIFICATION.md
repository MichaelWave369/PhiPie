# PHIPIE-03 — Raspberry Pi 5 first-boot qualification

Status: **field candidate preparation**

PHIPIE-03 is the first rung that requires a real Raspberry Pi 5. CI can build and
validate the field candidate, but CI cannot complete the hardware claim.

## Qualification target

The first target is deliberately narrow:

- Raspberry Pi 5 Model B;
- ARM64;
- removable storage flashed from the exact field candidate;
- HDMI display and keyboard for visible boot observation;
- ordinary wired Ethernet may be connected, but network success is not required for
  the first boot claim.

Compute Module 5 remains a separate later target.

## Field candidate behavior

The PHIPIE-03 image uses the same Pi 5 base as PHIPIE-02 and adds a bounded,
observation-only first-boot capture service.

On each boot it writes a unique receipt under:

```text
/boot/firmware/phipie-field/
```

When that mount is unavailable it falls back to:

```text
/var/lib/phipie/phipie-field/
```

The receipt records:

- boot ID;
- observed board model and compatible strings;
- kernel and machine architecture;
- PhiPie image marker;
- bounded network interface state without MAC or IP addresses;
- root mount and block-device structure;
- optional Raspberry Pi throttle/temperature observations when `vcgencmd` exists;
- explicit checks for Pi 5, ARM64 and the PHIPIE-03 field profile.

The receipt always contains:

```text
hardware_qualified = false
field_observation_only = true
```

The machine cannot qualify itself.

## Test sequence

1. Download the exact PHIPIE-03 field artifact from the green main-branch workflow.
2. Decompress the image and verify its SHA-256 against the artifact's `SHA256SUMS`.
3. Flash that exact raw image to removable media using Raspberry Pi Imager or another
   trusted imaging tool.
4. With power disconnected, insert the media into a Raspberry Pi 5.
5. Attach HDMI and a keyboard. Photograph or otherwise preserve the initial boot result.
6. Power on from a cold state.
7. Wait for the console message:
   `PHIPIE-03 FIELD CAPTURE COMPLETE`.
8. Preserve the first boot receipt.
9. Perform one clean reboot and wait for a second, different boot ID and capture-complete
   message.
10. Shut down cleanly, remove the media, and copy the `phipie-field` directory.
11. Run `scripts/field/validate-receipt.py` against each receipt.
12. Review the receipts, image identity and visual observation before recording a
    qualification result.

## Required evidence for completion

A PHIPIE-03 completion record must bind:

- exact PhiPie source commit;
- field workflow run ID;
- exact image SHA-256;
- board model as observed by the running kernel;
- two distinct boot IDs from cold boot + reboot;
- ARM64 architecture observation;
- image marker showing `PHIPIE_RUNG=PHIPIE-03` and `PHIPIE_PROFILE=field`;
- retained visual boot observation;
- failures or warnings encountered during the run.

A passing receipt is necessary but not sufficient. The evidence is reviewed as a set.

## Non-claims

PHIPIE-03 does not qualify:

- the PhiOS runtime, which is PHIPIE-04;
- PhiShell desktop graphics, which is PHIPIE-05;
- Wi-Fi, Bluetooth, GPIO, NVMe or every USB peripheral;
- sustained thermals or performance;
- Compute Module 5;
- secure boot or production provisioning.

## Current main-line PHIPIE-02 reference

The first merged PHIPIE-02 main build was workflow run `36952296786`, sourced from
PhiPie commit `4e0778cf90ed506cd82f63602e35cd9ecbad2b4e`.

Its raw minimal image SHA-256 was:

```text
194ba60378cd034f2fae9b83944c2902a1bd3c9a8c7d93aff4c941116de13201
```

That image proves construction only and is not the PHIPIE-03 field candidate.
