# Agent contribution contract

This repository is the ARM64 hardware/distribution layer for PhiOS.

## Non-negotiable boundaries

- Do not copy or fork PhiOS core into this repository.
- Do not modify or imply modification of the qualified PhiOS x86_64 release chain.
- Treat Raspberry Pi 5 and Compute Module 5 as separate hardware qualification targets.
- Do not convert build success, emulation success, or one-board success into a broader hardware claim.
- Preserve the PhiOS rule: **capability != authority**.
- Device identity, PhiBot identity, model identity, and operator identity are separate concepts.
- No agent receives root or publication authority merely because a tool exists.
- Security mechanisms such as secure boot or irreversible provisioning must remain opt-in research until explicitly qualified.

## Development order

Follow the current rung in `docs/ROADMAP.md`. Avoid broadening a rung to absorb future work.

Every implementation rung should define:

1. target identity;
2. exact inputs;
3. expected outputs;
4. refusal/failure behavior;
5. evidence to retain;
6. claims that remain unqualified.

PHIPIE-00 is documentation/contracts only.
