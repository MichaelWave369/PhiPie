# PHIPIE-01 reproducible test-fixture maintenance snapshot

Status: requalification candidate, not qualified merely by this document.

## Problem observed (2026-11-09)

Pinned PhiOS commit dad7a7d7cd53874926ad366f19d3fc0fa6b99a49 had memory test fixtures
with nominal expiry dates October 20-21, 2026. Non-expiration tests
therefore failed while the runtime correctly refused reads of expired
records. Observed failures: 10 in each full core matrix on ARM64 and
x86_64, plus 4 in the ARM64 memory-backend lane.

## Minimal upstream PhiOS maintenance input

- Repository: https://github.com/MichaelWave369/PhiOS
- Base commit: dad7a7d7cd53874926ad366f19d3fc0fa6b99a49
- Maintenance branch: support/phipie-01-memory-fixtures-nov2026
- New exact commit: 5befb71ede300783ab9888c24a604e2c886e818c
- Difference: one commit, exactly four files under tests/.
- Runtime/production source changes: NONE.
- Only five non-expiration fixture expiry fields were replaced by None.
- The dedicated expired-record test retains its explicit expired timestamp.
- This is NOT upstream PhiOS main and is not a qualified x86 release;
  changing the PHIPIE-01 source SHA is explicit and auditable.

Review compare:
https://github.com/MichaelWave369/PhiOS/compare/dad7a7d7cd53874926ad366f19d3fc0fa6b99a49...5befb71ede300783ab9888c24a604e2c886e818c

## Qualification and refusal

The normal PHIPIE-01 workflow must fetch this exact SHA, verify it,
run full Ruff/Mypy/Pytest on both x86_64 and aarch64, ARM64 governed
memory + native ledger backends, PhiShell and the final gate.

This maintenance input does NOT unfreeze broader PHIPIE-03 hardware
qualification and does not establish that a Pi 5 boots PhiOS.
The active dependency is still pinned and cannot float to current main.
Do not disable TTL safety, freeze production clocks, or skip failing tests.
If a future rebase is desired, review the much larger upstream delta as
a separate qualified change.
