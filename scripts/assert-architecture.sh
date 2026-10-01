#!/usr/bin/env bash
set -euo pipefail

EXPECTED="${1:?usage: assert-architecture.sh <x86_64|aarch64>}"
UNAME_ARCH="$(uname -m)"
DPKG_ARCH="$(dpkg --print-architecture 2>/dev/null || true)"
PY_ARCH="$(python - <<'PY'
import platform
print(platform.machine())
PY
)"

case "$EXPECTED" in
  x86_64)
    [[ "$UNAME_ARCH" == "x86_64" ]] || {
      echo "expected x86_64 runner, got $UNAME_ARCH" >&2
      exit 1
    }
    [[ -z "$DPKG_ARCH" || "$DPKG_ARCH" == "amd64" ]] || {
      echo "expected dpkg amd64, got $DPKG_ARCH" >&2
      exit 1
    }
    ;;
  aarch64)
    [[ "$UNAME_ARCH" == "aarch64" || "$UNAME_ARCH" == "arm64" ]] || {
      echo "expected ARM64 runner, got $UNAME_ARCH" >&2
      exit 1
    }
    [[ -z "$DPKG_ARCH" || "$DPKG_ARCH" == "arm64" ]] || {
      echo "expected dpkg arm64, got $DPKG_ARCH" >&2
      exit 1
    }
    ;;
  *)
    echo "unsupported expected architecture: $EXPECTED" >&2
    exit 1
    ;;
esac

echo "architecture verified: expected=$EXPECTED uname=$UNAME_ARCH python=$PY_ARCH dpkg=${DPKG_ARCH:-n/a}"
