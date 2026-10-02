#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep:
            raise ValueError(f"invalid env line in {path}: {raw!r}")
        values[key] = value
    return values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--phipie-source", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    image = Path(args.image).resolve()
    config = Path(args.config).resolve()
    phios = env_file(root / "deps/phios.env")
    builder = env_file(root / "deps/rpi-image-gen.env")

    if not re.fullmatch(r"[0-9a-f]{40}", args.phipie_source):
        raise SystemExit("PHIPIE source must be an exact lowercase 40-character commit SHA")

    config_text = config.read_text(encoding="utf-8")
    match = re.search(r"^\s*SOURCE_DATE_EPOCH:\s*(\d+)\s*$", config_text, re.MULTILINE)
    if not match:
        raise SystemExit("image config does not declare SOURCE_DATE_EPOCH")

    payload = {
        "schema": "phipie.image-manifest.v1",
        "rung": "PHIPIE-02",
        "target": "rpi5-arm64",
        "profile": "minimal",
        "phipie_source_commit": args.phipie_source,
        "phios_input": {
            "repository": phios["PHIOS_REPOSITORY"],
            "commit": phios["PHIOS_COMMIT"],
            "installed_in_image": False,
        },
        "image_builder": {
            "repository": builder["RPI_IMAGE_GEN_REPOSITORY"],
            "commit": builder["RPI_IMAGE_GEN_COMMIT"],
        },
        "config": {
            "path": str(config.relative_to(root)),
            "sha256": sha256(config),
            "source_date_epoch": int(match.group(1)),
        },
        "build_host": {
            "machine": platform.machine(),
            "system": platform.system(),
        },
        "image": {
            "name": image.name,
            "size_bytes": image.stat().st_size,
            "sha256": sha256(image),
        },
        "claims": {
            "image_constructed": True,
            "bit_for_bit_reproducibility_claimed": False,
            "raspberry_pi_5_boot_qualified": False,
            "raspberry_pi_5_hardware_qualified": False,
            "compute_module_5_qualified": False,
            "phios_runtime_installed": False,
        },
        "notes": [
            "The image builder is pinned by exact commit.",
            "The image uses the rpi-image-gen trixie-minbase suite, whose package repositories may advance.",
            "PHIPIE-02 therefore records exact artifact identity but does not claim future rebuilds are bit-for-bit identical.",
            "Physical boot and hardware observations begin at PHIPIE-03.",
        ],
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
