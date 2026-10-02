#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILDER_DIR="${PHIPIE_BUILDER_DIR:-$ROOT_DIR/tools/rpi-image-gen}"
DIST_DIR="${PHIPIE_DIST_DIR:-$ROOT_DIR/dist}"
PROFILE="${1:-minimal}"
SOURCE_DATE_EPOCH_EXPECTED="1790899924"

case "$PROFILE" in
  minimal)
    CONFIG="$ROOT_DIR/image/configs/phipie-rpi5-min.yaml"
    IMAGE_NAME="phipie-rpi5-arm64-min.img"
    ;;
  field)
    CONFIG="$ROOT_DIR/image/configs/phipie-rpi5-field.yaml"
    IMAGE_NAME="phipie-rpi5-arm64-field.img"
    ;;
  *)
    echo "unsupported PhiPie image profile: $PROFILE" >&2
    exit 1
    ;;
esac

bash "$ROOT_DIR/scripts/assert-architecture.sh" aarch64

if [[ ! -x "$BUILDER_DIR/rpi-image-gen" ]]; then
  echo "rpi-image-gen is not present at $BUILDER_DIR; run scripts/fetch-rpi-image-gen.sh first" >&2
  exit 1
fi

BASE_CONFIG="$ROOT_DIR/image/configs/phipie-rpi5-min.yaml"
if ! grep -Fxq "  SOURCE_DATE_EPOCH: $SOURCE_DATE_EPOCH_EXPECTED" "$BASE_CONFIG"; then
  echo "base image SOURCE_DATE_EPOCH drifted from the image contract" >&2
  exit 1
fi

rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"

(
  cd "$BUILDER_DIR"
  ./rpi-image-gen build -S "$ROOT_DIR/image" -c "$CONFIG"
)

mapfile -t images < <(find "$BUILDER_DIR/work" -type f -name "$IMAGE_NAME" -print)
if [[ "${#images[@]}" -ne 1 ]]; then
  printf 'expected exactly one %s, found %d\n' "$IMAGE_NAME" "${#images[@]}" >&2
  printf '%s\n' "${images[@]:-}" >&2
  exit 1
fi

cp --sparse=always "${images[0]}" "$DIST_DIR/$IMAGE_NAME"
bash "$ROOT_DIR/scripts/verify-image.sh" "$DIST_DIR/$IMAGE_NAME"

echo "PhiPie $PROFILE image ready: $DIST_DIR/$IMAGE_NAME"
