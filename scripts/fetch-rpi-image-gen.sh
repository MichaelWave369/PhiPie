#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCK_FILE="$ROOT_DIR/deps/rpi-image-gen.env"
DEST="${1:-$ROOT_DIR/tools/rpi-image-gen}"

if [[ ! -f "$LOCK_FILE" ]]; then
  echo "missing rpi-image-gen lock: $LOCK_FILE" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$LOCK_FILE"

: "${RPI_IMAGE_GEN_REPOSITORY:?RPI_IMAGE_GEN_REPOSITORY must be set}"
: "${RPI_IMAGE_GEN_COMMIT:?RPI_IMAGE_GEN_COMMIT must be set}"

if [[ ! "$RPI_IMAGE_GEN_COMMIT" =~ ^[0-9a-f]{40}$ ]]; then
  echo "RPI_IMAGE_GEN_COMMIT must be an exact 40-character lowercase SHA" >&2
  exit 1
fi

if [[ "$RPI_IMAGE_GEN_REPOSITORY" != "https://github.com/raspberrypi/rpi-image-gen.git" ]]; then
  echo "unexpected rpi-image-gen repository: $RPI_IMAGE_GEN_REPOSITORY" >&2
  exit 1
fi

rm -rf "$DEST"
mkdir -p "$(dirname "$DEST")"

git init -q "$DEST"
git -C "$DEST" remote add origin "$RPI_IMAGE_GEN_REPOSITORY"
git -C "$DEST" fetch --quiet --depth=1 origin "$RPI_IMAGE_GEN_COMMIT"
git -C "$DEST" checkout --quiet --detach FETCH_HEAD

ACTUAL="$(git -C "$DEST" rev-parse HEAD)"
if [[ "$ACTUAL" != "$RPI_IMAGE_GEN_COMMIT" ]]; then
  echo "rpi-image-gen source identity mismatch: expected=$RPI_IMAGE_GEN_COMMIT actual=$ACTUAL" >&2
  exit 1
fi

echo "rpi-image-gen source verified: $ACTUAL"
