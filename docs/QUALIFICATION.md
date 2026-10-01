# Qualification Model

PhiPie uses bounded evidence. A passing observation proves only the thing actually observed on the exact artifact and target under test.

## Evidence identity

A hardware qualification packet should eventually bind at minimum:

- PhiPie source commit;
- exact PhiOS dependency identity;
- image artifact digest;
- hardware model;
- firmware/kernel identity;
- storage medium;
- power/cooling configuration when relevant;
- boot mode/profile;
- test protocol version;
- retained logs/receipts.

## Qualification ladder

```text
source validates
   ↓
ARM64 software tests pass
   ↓
image builds
   ↓
image boots
   ↓
hardware devices observed
   ↓
desktop/node services validated
   ↓
persistence/reboot validated
   ↓
governance/refusal tests pass
   ↓
target becomes qualified for the tested scope
```

Skipping a rung does not inherit its claim.

## Required failure preservation

Failed boots, missing devices, degraded graphics, network failures, permission refusals and interrupted updates are evidence. Do not rewrite or discard them merely because a later attempt succeeds.

## Target separation

Raspberry Pi 5 and Compute Module 5 maintain separate hardware evidence.

A virtual ARM64 environment may validate software behavior but cannot qualify physical I/O, firmware, thermals, storage reliability, graphics, radio behavior or board-specific boot behavior.

## Security claims

Secure boot, encrypted state, hardware-bound keys and irreversible provisioning require their own explicit protocols. Development boards should remain recoverable until those protocols are frozen.
