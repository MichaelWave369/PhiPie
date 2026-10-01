#!/usr/bin/env bash
set -euo pipefail

required=(
  README.md
  LICENSE
  AGENTS.md
  deps/phios.env
  docs/PHIPIE_PLATFORM_CONTRACT.md
  docs/PHIPIE_01_ARM64_SOFTWARE_CI.md
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
  scripts/fetch-phios.sh
  scripts/assert-architecture.sh
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

if ! grep -Eq '^PHIOS_COMMIT=[0-9a-f]{40}$' deps/phios.env; then
  echo "deps/phios.env must pin PhiOS by an exact lowercase 40-character commit SHA" >&2
  exit 1
fi

if ! grep -Fxq 'PHIOS_REPOSITORY=https://github.com/MichaelWave369/PhiOS.git' deps/phios.env; then
  echo "deps/phios.env contains an unexpected PhiOS repository" >&2
  exit 1
fi

echo "PhiPie contract layout verified"
