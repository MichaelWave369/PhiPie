#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace").replace("\x00", "").strip()
    except OSError:
        return None


def read_bytes(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except OSError:
        return None


def parse_release(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    text = read_text(path)
    if text is None:
        return values
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if sep:
            values[key] = value
    return values


def run(command: list[str]) -> dict[str, Any]:
    executable = shutil.which(command[0])
    if executable is None:
        return {"available": False, "returncode": None, "stdout": "", "stderr": "command unavailable"}
    proc = subprocess.run(
        [executable, *command[1:]],
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )
    return {
        "available": True,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def network_snapshot(root: Path) -> list[dict[str, Any]]:
    base = root / "sys/class/net"
    if not base.exists():
        return []
    rows: list[dict[str, Any]] = []
    for entry in sorted(base.iterdir(), key=lambda p: p.name):
        rows.append(
            {
                "name": entry.name,
                "operstate": read_text(entry / "operstate"),
                "carrier": read_text(entry / "carrier"),
                "mtu": read_text(entry / "mtu"),
            }
        )
    return rows


def compatible_strings(root: Path) -> list[str]:
    raw = read_bytes(root / "proc/device-tree/compatible")
    if raw is None:
        raw = read_bytes(root / "sys/firmware/devicetree/base/compatible")
    if raw is None:
        return []
    return [part.decode("utf-8", errors="replace") for part in raw.split(b"\x00") if part]


def discover_output_root(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    for candidate in (Path("/boot/firmware"), Path("/boot")):
        if candidate.exists() and os.access(candidate, os.W_OK):
            return candidate
    return Path("/var/lib/phipie")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture bounded PHIPIE-03 boot evidence.")
    parser.add_argument("--root", default="/", help="Filesystem root for fixture testing.")
    parser.add_argument("--output-root", help="Override evidence output root.")
    args = parser.parse_args()

    root = Path(args.root)
    output_root = discover_output_root(args.output_root)
    output_dir = output_root / "phipie-field"
    output_dir.mkdir(parents=True, exist_ok=True)

    boot_id = read_text(root / "proc/sys/kernel/random/boot_id") or "unknown-boot"
    model = (
        read_text(root / "proc/device-tree/model")
        or read_text(root / "sys/firmware/devicetree/base/model")
        or "unknown"
    )
    machine = platform.machine()

    release = parse_release(root / "etc/phipie-release")
    uptime = read_text(root / "proc/uptime")

    model_match = model.startswith("Raspberry Pi 5")
    architecture_match = machine in {"aarch64", "arm64"}
    profile_match = release.get("PHIPIE_PROFILE") == "field"
    rung_match = release.get("PHIPIE_RUNG") == "PHIPIE-03"

    receipt: dict[str, Any] = {
        "schema": "phipie.field-boot.v1",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "field_observation_only": True,
        "hardware_qualified": False,
        "boot_id": boot_id,
        "host": {
            "hostname": socket.gethostname(),
            "machine": machine,
            "kernel_release": platform.release(),
            "kernel_version": platform.version(),
            "model": model,
            "compatible": compatible_strings(root),
            "uptime": uptime,
        },
        "phipie_release": release,
        "network": network_snapshot(root),
        "checks": {
            "raspberry_pi_5_model": model_match,
            "arm64_machine": architecture_match,
            "field_profile": profile_match,
            "phipie_03_rung": rung_match,
        },
        "commands": {
            "system_state": run(["systemctl", "is-system-running"]),
            "root_mount": run(["findmnt", "-J", "/"]),
            "block_devices": run(
                ["lsblk", "-J", "-o", "NAME,TYPE,SIZE,FSTYPE,MOUNTPOINTS,MODEL,TRAN"]
            ),
            "throttle": run(["vcgencmd", "get_throttled"]),
            "temperature": run(["vcgencmd", "measure_temp"]),
        },
        "result": (
            "candidate-observed"
            if model_match and architecture_match and profile_match and rung_match
            else "unexpected-target-or-profile"
        ),
        "qualification_note": (
            "This receipt records an observation only. Human review of exact image identity, "
            "boot evidence, and repeated-boot behavior is required before PHIPIE-03 is qualified."
        ),
    }

    receipt_path = output_dir / f"boot-{boot_id}.json"
    temp_path = receipt_path.with_suffix(".json.tmp")
    temp_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp_path.replace(receipt_path)

    marker_path = output_dir / f"CAPTURE-COMPLETE-{boot_id}.txt"
    marker_path.write_text(
        "\n".join(
            [
                "PHIPIE-03 FIELD CAPTURE COMPLETE",
                f"boot_id={boot_id}",
                f"model={model}",
                f"machine={machine}",
                f"result={receipt['result']}",
                "hardware_qualified=false",
                "",
            ]
        ),
        encoding="utf-8",
    )

    sums_path = output_dir / "SHA256SUMS"
    rows = []
    for path in sorted(output_dir.glob("boot-*.json")):
        rows.append(f"{sha256(path)}  {path.name}")
    for path in sorted(output_dir.glob("CAPTURE-COMPLETE-*.txt")):
        rows.append(f"{sha256(path)}  {path.name}")
    sums_path.write_text("\n".join(rows) + "\n", encoding="utf-8")

    try:
        with Path("/dev/tty1").open("w", encoding="utf-8") as tty:
            tty.write("\n\n")
            tty.write("========================================\n")
            tty.write("  PHIPIE-03 FIELD CAPTURE COMPLETE\n")
            tty.write(f"  boot: {boot_id}\n")
            tty.write(f"  result: {receipt['result']}\n")
            tty.write("  evidence: /boot/firmware/phipie-field/\n")
            tty.write("  hardware qualification: NOT YET\n")
            tty.write("========================================\n\n")
    except OSError:
        pass

    os.sync()
    print(receipt_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
