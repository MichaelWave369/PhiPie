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
  docs/PHIPIE_03_RPI5_BOOT_QUALIFICATION.md
  docs/ARCHITECTURE.md
  docs/QUALIFICATION.md
  docs/ROADMAP.md
  field/README.md
  image/README.md
  image/configs/phipie-rpi5-min.yaml
  image/configs/phipie-rpi5-field.yaml
  image/hooks/customize90-phipie
  image/field/collect_boot_evidence.py
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
  scripts/field/validate-receipt.py
  scripts/field/verify-candidate.sh
  scripts/field/verify-candidate.ps1
  tests/README.md
)

for path in "${required[@]}"; do
  if [[ ! -s "$path" ]]; then
    echo "missing or empty required file: $path" >&2
    exit 1
  fi
done

if grep -RInE 'PhiPie[[:space:]]*=[[:space:]]*PhiOS fork|capability[[:space:]]*=[[:space:]]*authority'   README.md AGENTS.md docs runtime platform image field; then
  echo "forbidden boundary text detected" >&2
  exit 1
fi

grep -Eq '^PHIOS_COMMIT=[0-9a-f]{40}$' deps/phios.env
grep -Fxq 'PHIOS_REPOSITORY=https://github.com/MichaelWave369/PhiOS.git' deps/phios.env
grep -Eq '^RPI_IMAGE_GEN_COMMIT=[0-9a-f]{40}$' deps/rpi-image-gen.env
grep -Fxq 'RPI_IMAGE_GEN_REPOSITORY=https://github.com/raspberrypi/rpi-image-gen.git' deps/rpi-image-gen.env

for path in   image/hooks/customize90-phipie   image/field/collect_boot_evidence.py   scripts/build-image.sh   scripts/verify-image.sh   scripts/write-image-manifest.py   scripts/field/validate-receipt.py   scripts/field/verify-candidate.sh
do
  if [[ ! -x "$path" ]]; then
    echo "expected executable file: $path" >&2
    exit 1
  fi
done

echo "PhiPie contract layout verified"
