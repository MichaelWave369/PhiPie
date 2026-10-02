#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_CHECKS = (
    "raspberry_pi_5_model",
    "arm64_machine",
    "field_profile",
    "phipie_03_rung",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a PHIPIE-03 field boot receipt.")
    parser.add_argument("receipt")
    args = parser.parse_args()

    path = Path(args.receipt)
    data = json.loads(path.read_text(encoding="utf-8"))

    if data.get("schema") != "phipie.field-boot.v1":
        raise SystemExit("unexpected receipt schema")
    if data.get("hardware_qualified") is not False:
        raise SystemExit("field receipt must never self-declare hardware qualification")
    if data.get("field_observation_only") is not True:
        raise SystemExit("field receipt must remain observation-only")

    checks = data.get("checks")
    if not isinstance(checks, dict):
        raise SystemExit("receipt checks missing")

    missing = [name for name in REQUIRED_CHECKS if name not in checks]
    if missing:
        raise SystemExit(f"receipt missing checks: {missing}")

    summary = {
        "boot_id": data.get("boot_id"),
        "model": data.get("host", {}).get("model"),
        "machine": data.get("host", {}).get("machine"),
        "result": data.get("result"),
        "checks": {name: checks[name] for name in REQUIRED_CHECKS},
    }
    print(json.dumps(summary, indent=2, sort_keys=True))

    if not all(checks[name] is True for name in REQUIRED_CHECKS):
        raise SystemExit("receipt is valid but does not match the PHIPIE-03 Pi 5 field target")
    if data.get("result") != "candidate-observed":
        raise SystemExit("receipt did not record candidate-observed")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
