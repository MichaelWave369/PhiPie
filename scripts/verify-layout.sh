#!/usr/bin/env bash
set -euo pipefail

required=(
  README.md
  LICENSE
  AGENTS.md
  docs/PHIPIE_PLATFORM_CONTRACT.md
  docs/ARCHITECTURE.md
  docs/QUALIFICATION.md
  docs/ROADMAP.md
  image/README.md
  platform/rpi5/README.md
  platform/cm5/README.md
  runtime/node/README.md
  runtime/identity/README.md
  runtime/missions/README.md
  runtime/governance/README.md
  tests/README.md
)

for path in "${required[@]}"; do
  if [[ ! -s "$path" ]]; then
    echo "missing or empty required file: $path" >&2
    exit 1
  fi
done

if grep -RInE 'PhiPie[[:space:]]*=[[:space:]]*PhiOS fork|capability[[:space:]]*=[[:space:]]*authority'   README.md AGENTS.md docs runtime platform image; then
  echo "forbidden boundary text detected" >&2
  exit 1
fi

echo "PHIPIE-00 layout verified"
