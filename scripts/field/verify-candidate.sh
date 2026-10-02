#!/usr/bin/env bash
set -euo pipefail

IMAGE="${1:?usage: verify-candidate.sh <image.img> <expected-sha256>}"
EXPECTED="${2:?usage: verify-candidate.sh <image.img> <expected-sha256>}"

if [[ ! "$EXPECTED" =~ ^[0-9a-fA-F]{64}$ ]]; then
  echo "expected SHA-256 must be exactly 64 hexadecimal characters" >&2
  exit 1
fi

ACTUAL="$(sha256sum "$IMAGE" | awk '{print $1}')"
printf 'expected=%s\nactual=%s\n' "$EXPECTED" "$ACTUAL"

if [[ "${ACTUAL,,}" != "${EXPECTED,,}" ]]; then
  echo "candidate image hash mismatch" >&2
  exit 1
fi

echo "candidate image identity verified"
