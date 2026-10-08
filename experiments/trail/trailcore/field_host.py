"""Privacy-limited, read-only Linux host snapshot for ΦTrail field testing.

No serial, MAC/BSSID/SSID, IP, hostname, exact GPS or operator identity.
This is a locally reported software view, not hardware root-of-trust evidence.
"""
from __future__ import annotations

from hashlib import sha256
import json
import platform
from pathlib import Path
import re
import time

from .field_witness import _hash


def _model_family(text: str) -> str:
    if "Raspberry Pi 5 Model B" in text:
        return "RPI5_REPORTED"
    if "Raspberry Pi Compute Module 5" in text:
        return "CM5_REPORTED"
    if text:
        return "LINUX_OTHER"
    return "UNKNOWN"


def capture_host(*, model_text: str | None = None, clock=None,
                 machine: str | None = None, kernel: str | None = None) -> dict:
    """No subprocesses, no filesystem write. `model_text` injection aids tests."""
    if model_text is None:
        try:
            model_text = Path("/proc/device-tree/model").read_bytes()[:256].decode(
                "utf-8", errors="replace").rstrip("\x00")
        except OSError:
            model_text = ""
    observed_at = clock() if clock is not None else time.time()
    machine = machine if machine is not None else platform.machine()
    kernel = kernel if kernel is not None else platform.release()
    # Deliberately coarse: no real board unique identity or exact build.
    arch = machine if machine in {"aarch64", "arm64", "x86_64", "AMD64"} else "OTHER"
    match = re.match(r"^(\d{1,3})\.(\d{1,3})", kernel)
    kernel_major_minor = (match.group(1)+"."+match.group(2)) if match else "UNKNOWN"
    import math
    try:
        safe_time = (observed_at if type(observed_at) in (float, int)
                     and math.isfinite(observed_at) and observed_at >= 0 else None)
    except (TypeError, ValueError, OverflowError):
        safe_time = None
    result = {
        "schema": "phipie-trail-host-snapshot/v0.1",
        "platform": _model_family(model_text),
        "architecture": arch,
        "kernel_major_minor": kernel_major_minor,
        "captured_at_s": safe_time,
        "evidence_origin": "LOCAL_LINUX",
        "hardware_attested": False,
        "clock_trusted": False,
        "unique_identity_disclosed": False,
        "read_only": True,
    }
    result["snapshot_sha256"] = _hash(result)
    return result
