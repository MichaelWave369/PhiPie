#!/usr/bin/env bash
# Preflight: only integrity-verified host build dependencies; no board qualification.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILDER="${PHIPIE_BUILDER_DIR:-${ROOT}/tools/rpi-image-gen}"
readonly ZSTD_SHA="eb33e51f49a15e023950cd7825ca74a4a2b43db8354825ac24fc1b7ee09e6fa3"
readonly SYFT_SHA="6c0466811541ea03add5213a60a1562f0851e4c0b0ecfdee1a694a9455285900"

verify_sha() {
  local file="$1" sha="$2"
  [[ -f "$file" ]] && printf '%s  %s\n' "$sha" "$file" | sha256sum --check --status
}

download_verified() {
  local destination="$1" expected_sha="$2"
  shift 2
  local url attempt temp
  mkdir -p -- "$(dirname "$destination")"
  if verify_sha "$destination" "$expected_sha"; then
    echo "Verified acquisition cache: $(basename "$destination")"
    return 0
  fi
  rm -f -- "$destination"
  for url in "$@"; do
    for ((attempt = 1; attempt <= ${PHIPIE_FETCH_ATTEMPTS:-2}; attempt++)); do
      temp="$(mktemp "${destination}.part.XXXXXXXX")"
      if curl --fail --location --silent --show-error \
          --retry 3 --retry-all-errors --retry-delay 2 \
          --connect-timeout 20 --max-time 150 \
          --header 'Accept: application/octet-stream' \
          --output "$temp" "$url"; then
        if verify_sha "$temp" "$expected_sha"; then
          mv -f -- "$temp" "$destination"
          echo "Integrity verified: $(basename "$destination")"
          return 0
        fi
        echo "Rejected SHA-256 mismatch from $url" >&2
      else
        echo "Fetch attempt ${attempt} failed: $url" >&2
      fi
      rm -f -- "$temp"
      if ((attempt < ${PHIPIE_FETCH_ATTEMPTS:-2})); then
        sleep "${PHIPIE_FETCH_RETRY_DELAY_SEC:-5}"
      fi
    done
  done
  echo "No source matched pinned SHA-256 for $(basename "$destination")" >&2
  return 1
}

if [[ "${1:-}" == "--self-test" ]]; then
  tempdir="$(mktemp -d)"
  trap 'rm -rf -- "$tempdir"' EXIT
  printf 'known fixture' > "$tempdir/original"
  digest="$(sha256sum "$tempdir/original" | cut -d' ' -f1)"
  PHIPIE_FETCH_ATTEMPTS=1 PHIPIE_FETCH_RETRY_DELAY_SEC=0 \
    download_verified "$tempdir/cache" "$digest" "file://${tempdir}/original"
  cmp "$tempdir/original" "$tempdir/cache"
  printf 'corrupt payload' > "$tempdir/original"
  rm -f -- "$tempdir/cache"
  if PHIPIE_FETCH_ATTEMPTS=1 PHIPIE_FETCH_RETRY_DELAY_SEC=0 \
      download_verified "$tempdir/cache" "$digest" "file://${tempdir}/original"; then
    echo "ERROR: corrupted acquisition was accepted" >&2
    exit 1
  fi
  [[ ! -e "$tempdir/cache" ]] || { echo "ERROR: corrupt cache exists" >&2; exit 1; }
  echo "Integrity-gated acquisition self-test passed"
  exit 0
fi

[[ "${1:-}" == "" ]] || { echo "usage: $0 [--self-test]" >&2; exit 2; }
[[ -s "${BUILDER}/package/zstd/zstd-1.5.7.meta" ]] || {
  echo "Pinned rpi-image-gen source missing; fetch builder first" >&2; exit 1;
}
[[ -x "${BUILDER}/bin/vfetch" ]] || { echo "Pinned vfetch missing" >&2; exit 1; }

grep -Fxq \
  "zstd-1.5.7.tar.gz sha256:${ZSTD_SHA} https://github.com/facebook/zstd/releases/download/v1.5.7/zstd-1.5.7.tar.gz" \
  "${BUILDER}/package/zstd/zstd-1.5.7.meta" || {
    echo "Unexpected zstd pin in builder; refuse unreviewed toolchain drift" >&2
    exit 1
  }

download_verified "${BUILDER}/work/cache/zstd-1.5.7.tar.gz" "$ZSTD_SHA" \
  "https://github.com/facebook/zstd/releases/download/v1.5.7/zstd-1.5.7.tar.gz" \
  "https://vie.at.distfiles.macports.org/zstd/zstd-1.5.7.tar.gz"

# Leave upstream SBOM hook enabled by preinstalling the exact verified Syft.
tempdir="$(mktemp -d)"
trap 'rm -rf -- "$tempdir"' EXIT
download_verified "$tempdir/syft_1.51.0_linux_arm64.tar.gz" "$SYFT_SHA" \
  "https://github.com/anchore/syft/releases/download/v1.51.0/syft_1.51.0_linux_arm64.tar.gz" \
  "https://api.github.com/repos/anchore/syft/releases/assets/508878652"

tar -xOzf "$tempdir/syft_1.51.0_linux_arm64.tar.gz" syft > "$tempdir/syft"
chmod 0755 "$tempdir/syft"
sudo install -m 0755 "$tempdir/syft" /usr/local/bin/syft
/usr/local/bin/syft --version | grep -F '1.51.0' || {
  echo "Installed Syft does not match pinned version 1.51.0" >&2
  exit 1
}
echo "Verified build assets staged; source and SBOM gates remain enabled"
