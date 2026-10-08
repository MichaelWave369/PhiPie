"""PhiPie Trail PR18: strictly local eight-file ping provenance checker.

No sockets, router changes, actuator calls or claimed hardware qualification.
Read-only extension of #17: old seven-file witness manifests remain unchanged.
"""
from __future__ import annotations

from hashlib import sha256
import math
import os
from pathlib import Path
import stat
from typing import Any

from .evidence_binding import (
    FILE_RE, MANIFEST_CONTRACT, SLOTS, _read_dir_file,
    manifest_template, verify_local_bundle,
)
from .field_witness import _hash
from .linux_radio import _id, _private_ipv4
from .soma_observation import canonical_json

CONTRACT = "phipie-trail-probe-bundle-assessment/v0.1"
MANIFEST = "phipie-trail-private-probe-manifest/v0.1"
ALL_SLOTS = (*SLOTS, "icmp_probe")


def probe_manifest_template(test_id: str = "trial-001") -> dict[str, Any]:
    obj = manifest_template(test_id)
    obj["contract"] = MANIFEST
    obj["files"]["icmp_probe"] = "icmp-probe.json"
    return obj


def _finite(x: Any, lo: float, hi: float) -> bool:
    if type(x) not in (int, float):
        return False
    try:
        return math.isfinite(x) and lo <= x <= hi
    except (TypeError, ValueError, OverflowError):
        return False


def _valid_probe(probe: Any, path: Any) -> bool:
    if not isinstance(probe, dict) or not isinstance(path, dict):
        return False
    if set(probe) != {
        "schema", "status", "reason", "readonly", "motor_authority",
        "network_change_authority", "physical_deployment_authority",
        "interface", "target", "metrics", "provenance", "evidence_sha256",
    }:
        return False
    if (probe["schema"] != "phipie-trail-linux-radio-observer/v0.1"
        or probe["status"] != "OBSERVED_ADVISORY_ONLY"
        or probe["reason"] is not None or probe["readonly"] is not True
        or probe["motor_authority"] is not False
        or probe["network_change_authority"] is not False
        or probe["physical_deployment_authority"] is not False
        or not _id(probe["interface"], iface=True)
        or not _private_ipv4(probe["target"])):
        return False
    if probe["provenance"] != {
        "source": "operator-approved-icmp", "traffic_generated": True,
        "measured_throughput": False, "path_proven": False,
    }:
        return False
    m = probe["metrics"]
    if not isinstance(m, dict) or set(m) != {
        "probe_rtt_avg_ms", "probe_packet_loss_pct", "sent", "received",
        "observed_mbps",
    }:
        return False
    if (type(m["sent"]) is not int or m["sent"] != 3
        or type(m["received"]) is not int or not 1 <= m["received"] <= 3
        or m["observed_mbps"] is not None
        or not _finite(m["probe_rtt_avg_ms"], 0, 60000)
        or not _finite(m["probe_packet_loss_pct"], 0, 100)
        or abs(m["probe_packet_loss_pct"] - 100 * (3 - m["received"]) / 3) > 0.2):
        return False
    try:
        digest = sha256(canonical_json(
            {k: v for k, v in probe.items() if k != "evidence_sha256"}
        )).hexdigest()
    except (TypeError, ValueError, OverflowError):
        return False
    if not isinstance(probe["evidence_sha256"], str) or digest != probe["evidence_sha256"]:
        return False
    return (
        path.get("schema") == "phipie-trail-path-evidence/v0.1"
        and path.get("kind") == "ICMP"
        and path.get("independent_test_run") is True
        and path.get("evidence_origin") == "OPERATOR_RECORDED_INDEPENDENT"
        and path.get("throughput_mbps") is None
        and path.get("rtt_avg_ms") == m["probe_rtt_avg_ms"]
        and path.get("packet_loss_pct") == m["probe_packet_loss_pct"]
    )


def verify_probe_bundle(witness: Any, manifest: Any,
                        evidence_dir: str | Path) -> dict[str, Any]:
    checks = {slot: "NOT_CHECKED" for slot in ALL_SLOTS}
    reasons: list[str] = []
    if (not isinstance(manifest, dict)
        or set(manifest) != {"contract", "test_id", "files"}
        or manifest.get("contract") != MANIFEST
        or not isinstance(witness, dict)
        or manifest.get("test_id") != witness.get("test_id")
        or not isinstance(manifest.get("files"), dict)
        or set(manifest["files"]) != set(ALL_SLOTS)
        or any(not isinstance(name, str) or FILE_RE.fullmatch(name) is None
               for name in manifest["files"].values())
        or len(set(manifest["files"].values())) != len(ALL_SLOTS)):
        reasons.append("INVALID_PROBE_MANIFEST")
    else:
        legacy = {
            "contract": MANIFEST_CONTRACT,
            "test_id": manifest["test_id"],
            "files": {k: manifest["files"][k] for k in SLOTS},
        }
        prior = verify_local_bundle(witness, legacy, evidence_dir)
        checks.update(prior["checks"])
        if prior["status"] != "LOCAL_EVIDENCE_MATCH":
            reasons.append("SEVEN_FILE_BASELINE_HOLD")
        dirfd = None
        try:
            directory = Path(evidence_dir)
            if directory.is_symlink():
                raise ValueError("symlink directory")
            flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
            dirfd = os.open(directory, flags)
            st = os.fstat(dirfd)
            if not stat.S_ISDIR(st.st_mode):
                raise ValueError("non-directory")
            if os.name == "posix" and (st.st_uid != os.geteuid() or st.st_mode & 0o077):
                raise PermissionError("directory not private")
            probe, _ = _read_dir_file(dirfd, manifest["files"]["icmp_probe"])
            path, _ = _read_dir_file(dirfd, manifest["files"]["path_test"])
            checks["icmp_probe"] = "MATCH" if _valid_probe(probe, path) else "HOLD"
            if checks["icmp_probe"] != "MATCH":
                reasons.append("PROBE_TO_PATH_MISMATCH")
        except (OSError, ValueError, TypeError, PermissionError, UnicodeError):
            checks["icmp_probe"] = "HOLD"
            reasons.append("PROBE_UNREADABLE_OR_UNSAFE")
        finally:
            if dirfd is not None:
                os.close(dirfd)
    complete = not reasons and all(v == "MATCH" for v in checks.values())
    result = {
        "contract": CONTRACT,
        "status": "LOCAL_PROBE_EVIDENCE_MATCH" if complete else "HOLD",
        "reasons": sorted(set(reasons)),
        "checks": checks,
        "witness_sha256": _hash(witness),
        "manifest_sha256": _hash(manifest),
        "local_file_consistency_only": True,
        "probe_output_locally_consistent": complete,
        "host_attested": False,
        "sender_authenticated": False,
        "physical_hardware_qualified": False,
        "routed_network_verified": False,
        "mesh_transport_verified": False,
        "measured_throughput": False,
        "emergency_coverage_verified": False,
        "network_change_authorized": False,
        "rover_motion_authorized": False,
        "soma_runtime_wired": False,
    }
    result["assessment_sha256"] = _hash(result)
    return result
