#!/usr/bin/env bash
set -euo pipefail

required=(
  README.md
  LICENSE
  AGENTS.md
  deps/phios.env
  deps/rpi-image-gen.env
  docs/PHIPIE_PLATFORM_CONTRACT.md
  docs/PHIPIE_01_ARM64_SOFTWARE_CI.md
  docs/PHIPIE_02_MINIMAL_IMAGE.md
  docs/ARCHITECTURE.md
  docs/QUALIFICATION.md
  docs/ROADMAP.md
  image/README.md
  image/configs/phipie-rpi5-min.yaml
  image/hooks/customize90-phipie
  platform/rpi5/README.md
  platform/cm5/README.md
  runtime/node/README.md
  runtime/identity/README.md
  runtime/missions/README.md
  runtime/governance/README.md
  scripts/fetch-phios.sh
  scripts/fetch-rpi-image-gen.sh
  scripts/assert-architecture.sh
  scripts/build-image.sh
  scripts/verify-image.sh
  scripts/write-image-manifest.py
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

grep -Eq '^PHIOS_COMMIT=[0-9a-f]{40}$' deps/phios.env
grep -Fxq 'PHIOS_REPOSITORY=https://github.com/MichaelWave369/PhiOS.git' deps/phios.env
grep -Eq '^RPI_IMAGE_GEN_COMMIT=[0-9a-f]{40}$' deps/rpi-image-gen.env
grep -Fxq 'RPI_IMAGE_GEN_REPOSITORY=https://github.com/raspberrypi/rpi-image-gen.git' deps/rpi-image-gen.env

if [[ ! -x image/hooks/customize90-phipie ]]; then
  echo "PhiPie image hook must be executable" >&2
  exit 1
fi

echo "PhiPie contract layout verified"
