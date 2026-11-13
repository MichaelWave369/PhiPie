# PhiPie image-build dependency acquisition (PHIPIE-02 / PHIPIE-03)

Status: infrastructure hardening only. This does not qualify physical hardware.

On November 9, 2026, the image builds failed on HTTP 504 from the GitHub
release asset CDN, affecting zstd 1.5.7 and Syft 1.51.0.

## Integrity-preserving preflight

- scripts/prefetch-image-assets.sh verifies the existing pinned upstream
  zstd metadata, then fetches the identical source archive using retries
  and a MacPorts distfiles alternate URL.
- The SHA-256 must match
  eb33e51f49a15e023950cd7825ca74a4a2b43db8354825ac24fc1b7ee09e6fa3.
  The builder re-verifies this archive using its own vfetch mechanism.
- Syft 1.51.0 ARM64 is downloaded from the direct release URL or the
  public GitHub releases API asset endpoint (ID 508878652). Its tarball
  must match SHA-256
  6c0466811541ea03add5213a60a1562f0851e4c0b0ecfdee1a694a9455285900,
  the digest published in the GitHub release asset metadata.
- Only the verified Syft executable is installed to the CI runner.
  The upstream SBOM generation hook remains enabled.
- All sources and digests are pinned. If neither route works, the build
  continues to fail rather than using unchecked bytes.

## Local contract-only test

    bash -n scripts/prefetch-image-assets.sh
    bash scripts/prefetch-image-assets.sh --self-test

The local self-test checks valid-cache acceptance and corrupted-download
refusal with file:// fixtures, without network calls.

## Explicit non-claims

A successful checksum preflight does not imply the Pi image built, booted,
or passed field qualification. PHIPIE-03 remains a field candidate until
physical tests provide evidence. PHIPIE-01 has an independent pinned PhiOS
revision containing expired memory-test fixtures; that dependency must be
requalified separately, not patched silently or clock-frozen.

The build helper never controls power, battery electronics, or GPIO.
