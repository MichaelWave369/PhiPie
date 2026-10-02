#!/usr/bin/env bash
set -euo pipefail

IMAGE="${1:?usage: verify-image.sh <image.img>}"

if [[ ! -f "$IMAGE" ]]; then
  echo "image does not exist: $IMAGE" >&2
  exit 1
fi

SIZE="$(stat -c '%s' "$IMAGE")"
if (( SIZE < 67108864 )); then
  echo "image is unexpectedly small: $SIZE bytes" >&2
  exit 1
fi

FILE_REPORT="$(file "$IMAGE")"
FDISK_REPORT="$(fdisk -l "$IMAGE")"

printf '%s\n' "$FILE_REPORT"
printf '%s\n' "$FDISK_REPORT"

if ! grep -Eq 'Linux filesystem|Linux' <<<"$FDISK_REPORT"; then
  echo "partition report does not contain a Linux partition" >&2
  exit 1
fi

if ! grep -Eqi 'FAT|W95|EFI' <<<"$FDISK_REPORT"; then
  echo "partition report does not contain a FAT/boot-style partition" >&2
  exit 1
fi

sha256sum "$IMAGE"
echo "minimal image structure verified"
