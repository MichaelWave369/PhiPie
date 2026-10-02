# PHIPIE-03 field evidence

This directory documents and validates evidence returned by a physical Raspberry Pi 5.

The embedded collector is stored under `image/field/`; host-side validation helpers are
under `scripts/field/`.

## Evidence rule

A field receipt is an observation, not a self-issued qualification.

```text
receipt exists
!=
receipt matches target
!=
artifact identity verified
!=
hardware qualified
```

PHIPIE-03 requires two distinct physical boot receipts plus the exact image identity and
a retained visual boot observation before the rung can be closed.
