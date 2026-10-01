# PhiPie runtime

This directory is reserved for PhiPie-specific node services that bridge hardware/platform concerns into PhiOS contracts.

It must not duplicate PhiOS governance logic.

Subareas:

- `node/` — node status and lifecycle;
- `identity/` — device/install pairing surfaces;
- `missions/` — bounded mission transport/execution adapters;
- `governance/` — platform enforcement adapters, not policy invention.
