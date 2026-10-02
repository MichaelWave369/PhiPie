#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCK_FILE="$ROOT_DIR/deps/phios.env"
DEST="${1:-$ROOT_DIR/upstream/PhiOS}"

if [[ ! -f "$LOCK_FILE" ]]; then
  echo "missing PhiOS lock: $LOCK_FILE" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$LOCK_FILE"

: "${PHIOS_REPOSITORY:?PHIOS_REPOSITORY must be set}"
: "${PHIOS_COMMIT:?PHIOS_COMMIT must be set}"

if [[ ! "$PHIOS_COMMIT" =~ ^[0-9a-f]{40}$ ]]; then
  echo "PHIOS_COMMIT must be an exact 40-character lowercase SHA" >&2
  exit 1
fi

if [[ "$PHIOS_REPOSITORY" != "https://github.com/MichaelWave369/PhiOS.git" ]]; then
  echo "unexpected PhiOS repository: $PHIOS_REPOSITORY" >&2
  exit 1
fi

rm -rf "$DEST"
mkdir -p "$(dirname "$DEST")"

git init -q "$DEST"
git -C "$DEST" remote add origin "$PHIOS_REPOSITORY"
git -C "$DEST" fetch --quiet --depth=1 origin "$PHIOS_COMMIT"
git -C "$DEST" checkout --quiet --detach FETCH_HEAD

ACTUAL="$(git -C "$DEST" rev-parse HEAD)"
if [[ "$ACTUAL" != "$PHIOS_COMMIT" ]]; then
  echo "PhiOS source identity mismatch: expected=$PHIOS_COMMIT actual=$ACTUAL" >&2
  exit 1
fi

echo "PhiOS source verified: $ACTUAL"
