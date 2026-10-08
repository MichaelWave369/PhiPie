"""Offline ΦTrail PR17: bind witness SHA claims to private local evidence files.

Only verifies local file integrity and internal consistency, NOT origin, physical
Pi identity, authenticated radio measurements, HMAC signature possession,
network transport, location consent, or safety certification. No network IO.
"""
from __future__ import annotations

import json
import os
import stat
from hashlib import sha256
from pathlib import Path
import re
from typing import Any

from .field_witness import _hash, assess_witness
from .soma_observation import canonical_json
from .two_node_pilot import _strict_pairs, _refuse_constant

CONTRACT = "phipie-trail-evidence-binding/v0.1"
MANIFEST_CONTRACT = "phipie-trail-private-evidence-manifest/v0.1"
PATH_CONTRACT = "phipie-trail-path-evidence/v0.1"
SLOTS = (
    "sender_host", "sender_radio", "receiver_host", "receiver_radio",
    "handoff_packet", "handoff_receipt", "path_test",
)
FILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\.json$")
MAX_BYTES = 16_384


def manifest_template(test_id: str = "trial-001") -> dict[str, Any]:
    return {
        "contract": MANIFEST_CONTRACT,
        "test_id": test_id,
        "files": {
            "sender_host": "sender-host.json",
            "sender_radio": "sender-radio.json",
            "receiver_host": "receiver-host.json",
            "receiver_radio": "receiver-radio.json",
            "handoff_packet": "radio-packet.json",
            "handoff_receipt": "receive-receipt.json",
            "path_test": "path-observation.json",
        },
    }


def _read_dir_file(dirfd: int, name: str) -> tuple[dict[str, Any], bytes]:
    if not isinstance(name, str) or FILE_RE.fullmatch(name) is None:
        raise ValueError("invalid evidence filename")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NONBLOCK", 0)
    fd = os.open(name, flags, dir_fd=dirfd)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
            raise ValueError("unsafe evidence type/size")
        if os.name == "posix" and (info.st_uid != os.geteuid() or info.st_mode & 0o077):
            raise PermissionError("private evidence must be owned and mode 0600")
        with os.fdopen(os.dup(fd), "rb") as f:
            raw = f.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("oversize evidence")
        item = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_pairs,
                          parse_constant=_refuse_constant)
        if not isinstance(item, dict):
            raise ValueError("evidence must be JSON object")
        return item, raw
    finally:
        os.close(fd)


def _reported_radio(item: dict[str, Any]) -> dict[str, Any] | None:
    if item.get("schema") == "phipie-trail-linux-radio-observer/v0.1":
        return item
    if set(item) == {"mode", "radio"} and item["mode"] == "READONLY_LOCAL_OBSERVER":
        inner = item["radio"]
        if isinstance(inner, dict):
            return inner
    return None


def _valid_host(host: dict, expected: dict) -> bool:
    fields = {
        "schema", "platform", "architecture", "kernel_major_minor",
        "captured_at_s", "evidence_origin", "hardware_attested",
        "clock_trusted", "unique_identity_disclosed", "read_only",
        "snapshot_sha256",
    }
    if set(host) != fields or host["schema"] != "phipie-trail-host-snapshot/v0.1":
        return False
    inner = {k: v for k, v in host.items() if k != "snapshot_sha256"}
    return (
        host["snapshot_sha256"] == _hash(inner) == expected["host_snapshot_sha256"]
        and host["platform"] == expected["platform"]
        and host["evidence_origin"] == expected["evidence_origin"]
        and host["hardware_attested"] is False and host["clock_trusted"] is False
        and host["unique_identity_disclosed"] is False and host["read_only"] is True
    )


def _valid_radio(item: dict, expected: dict) -> bool:
    report = _reported_radio(item)
    if report is None or report.get("schema") != "phipie-trail-linux-radio-observer/v0.1":
        return False
    if report.get("status") not in ("COMPLETE", "PARTIAL"):
        return False
    if (report.get("readonly") is not True
        or report.get("motor_authority") is not False
        or report.get("network_change_authority") is not False
        or report.get("physical_deployment_authority") is not False):
        return False
    prov = report.get("provenance")
    if (not isinstance(prov, dict)
        or prov.get("reader") != "linux-iw-readonly"
        or prov.get("origin_authenticated") is not False):
        return False
    if not isinstance(report.get("metrics"), dict):
        return False
    inner = {k: v for k, v in report.items() if k != "evidence_sha256"}
    try:
        calculated = sha256(canonical_json(inner)).hexdigest()
    except (TypeError, ValueError, OverflowError):
        return False
    return report.get("evidence_sha256") == calculated == expected["radio_report_sha256"]


def _valid_packet(packet: dict, sender: dict, witness: dict, raw: bytes) -> bool:
    sig = packet.get("signature")
    if (packet.get("contract") != "phipie-trail-soma-observation/v0.1"
        or packet.get("organ") != "sense.radio"
        or packet.get("node_id") != sender["node_id"]
        or not isinstance(sig, dict) or sig.get("alg") != "HMAC-SHA256"
        or not isinstance(sig.get("mac_hex"), str)
        or re.fullmatch(r"[0-9a-f]{64}", sig["mac_hex"]) is None):
        return False
    return sha256(raw).hexdigest() == witness["handoff"]["packet_sha256"]


def _receipt_body(receipt_file: dict) -> dict | None:
    if receipt_file.get("status") != "ACCEPTED_ADVISORY_ONLY":
        return None
    if (receipt_file.get("networkChangeAllowed") is not False
        or receipt_file.get("roverMotionAllowed") is not False
        or receipt_file.get("fieldIdentityAttested") is not False
        or receipt_file.get("radioMeasurementAttested") is not False
        or receipt_file.get("networkTransportEstablished") is not False):
        return None
    r = receipt_file.get("receipt")
    return r if isinstance(r, dict) else None


def _valid_receipt(item: dict, packet: dict, witness: dict) -> bool:
    r = _receipt_body(item)
    if r is None or r.get("contract") != "phipie-trail-soma-observation-receipt/v0.1":
        return False
    if (r.get("type") != "ObservationReceipt"
        or r.get("organ") != "sense.radio"
        or r.get("authentication") != "LAB_KEYRING_HMAC_ONLY"
        or r.get("somaRuntimeWired") is not False
        or any(r.get(k) is not False for k in (
            "actionAuthorized", "authorityGranted", "mayInvokeTools", "mayIssueHardwareCommands"
        )) or r.get("safetyPlaneUnaffected") is not True):
        return False
    body = {k: v for k, v in r.items() if k != "receipt_sha256"}
    try:
        if sha256(canonical_json(body)).hexdigest() != r.get("receipt_sha256"):
            return False
        unsigned = {k: v for k, v in packet.items() if k != "signature"}
        digest = sha256(canonical_json(unsigned)).hexdigest()
    except (TypeError, ValueError, OverflowError):
        return False
    return (
        r.get("receipt_sha256") == witness["handoff"]["receive_receipt_sha256"]
        and r.get("evidence_sha256") == digest
        and all(r.get(k) == packet.get(k) for k in (
            "node_id", "site_id", "observation_id", "organ", "sequence", "observed_at_s"
        ))
    )


def _valid_path(item: dict, raw: bytes, witness: dict) -> bool:
    expected = witness["path_test"]
    if set(item) != {
        "schema", "kind", "packet_loss_pct", "rtt_avg_ms", "throughput_mbps",
        "independent_test_run", "evidence_origin",
    }:
        return False
    if (item["schema"] != PATH_CONTRACT
        or item["evidence_origin"] != "OPERATOR_RECORDED_INDEPENDENT"
        or item["independent_test_run"] is not True
        or sha256(raw).hexdigest() != expected["evidence_sha256"]):
        return False
    return all(item.get(k) == expected.get(k) for k in (
        "kind", "packet_loss_pct", "rtt_avg_ms", "throughput_mbps", "independent_test_run"
    ))


def verify_local_bundle(witness: Any, manifest: Any, evidence_dir: str | Path) -> dict[str, Any]:
    """Checks local file consistency; output never contains raw evidence or paths."""
    reasons: list[str] = []
    checks = {slot: "NOT_CHECKED" for slot in SLOTS}
    baseline = assess_witness(witness)
    if baseline["status"] != "OPERATOR_REVIEW_CANDIDATE":
        reasons.append("FIELD_WITNESS_INCOMPLETE")
    if (not isinstance(manifest, dict) or set(manifest) != {"contract", "test_id", "files"}
        or manifest.get("contract") != MANIFEST_CONTRACT
        or not isinstance(witness, dict) or manifest.get("test_id") != witness.get("test_id")
        or not isinstance(manifest.get("files"), dict)
        or set(manifest["files"]) != set(SLOTS)
        or any(not isinstance(name, str) or FILE_RE.fullmatch(name) is None
               for name in manifest["files"].values())
        or len(set(manifest["files"].values())) != len(SLOTS)):
        reasons.append("INVALID_PRIVATE_MANIFEST")
    else:
        try:
            directory = Path(evidence_dir)
            if directory.is_symlink():
                raise ValueError("symlink evidence directory")
            flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
            dirfd = os.open(directory, flags)
            try:
                info = os.fstat(dirfd)
                if not stat.S_ISDIR(info.st_mode):
                    raise ValueError("not directory")
                if os.name == "posix" and (
                    info.st_uid != os.geteuid() or info.st_mode & 0o077
                ):
                    raise PermissionError("evidence directory must be owner only")
                records: dict[str, tuple[dict, bytes]] = {}
                for slot in SLOTS:
                    try:
                        records[slot] = _read_dir_file(dirfd, manifest["files"][slot])
                        checks[slot] = "READ"
                    except (OSError, ValueError, TypeError, UnicodeError, PermissionError):
                        checks[slot] = "HOLD"
                        reasons.append(slot.upper() + "_UNREADABLE_OR_UNSAFE")
            finally:
                os.close(dirfd)
        except (OSError, ValueError, TypeError, PermissionError):
            reasons.append("PRIVATE_EVIDENCE_DIRECTORY_UNSAFE")
            records = {}
        if isinstance(witness, dict) and isinstance(witness.get("nodes"), list):
            nodes = {
                n.get("role"): n for n in witness["nodes"]
                if isinstance(n, dict) and isinstance(n.get("role"), str)
            }
        else:
            nodes = {}
        for role in ("sender", "receiver"):
            for suffix in ("host", "radio"):
                slot = role + "_" + suffix
                if slot not in records or role not in nodes:
                    continue
                item, _ = records[slot]
                valid = (_valid_host(item, nodes[role]) if suffix == "host"
                         else _valid_radio(item, nodes[role]))
                checks[slot] = "MATCH" if valid else "HOLD"
                if not valid:
                    reasons.append(slot.upper() + "_EVIDENCE_MISMATCH")
        if "handoff_packet" in records and "sender" in nodes and baseline["status"] == "OPERATOR_REVIEW_CANDIDATE":
            packet, raw = records["handoff_packet"]
            valid = _valid_packet(packet, nodes["sender"], witness, raw)
            checks["handoff_packet"] = "MATCH" if valid else "HOLD"
            if not valid:
                reasons.append("HANDOFF_PACKET_MISMATCH")
        if "handoff_receipt" in records and "handoff_packet" in records and baseline["status"] == "OPERATOR_REVIEW_CANDIDATE":
            receipt, _ = records["handoff_receipt"]
            packet, _ = records["handoff_packet"]
            valid = _valid_receipt(receipt, packet, witness)
            checks["handoff_receipt"] = "MATCH" if valid else "HOLD"
            if not valid:
                reasons.append("HANDOFF_RECEIPT_MISMATCH")
        if "path_test" in records and baseline["status"] == "OPERATOR_REVIEW_CANDIDATE":
            path, raw = records["path_test"]
            valid = _valid_path(path, raw, witness)
            checks["path_test"] = "MATCH" if valid else "HOLD"
            if not valid:
                reasons.append("PATH_EVIDENCE_MISMATCH")

    result = {
        "contract": CONTRACT,
        "status": "LOCAL_EVIDENCE_MATCH" if not reasons and all(x == "MATCH" for x in checks.values()) else "HOLD",
        "reasons": sorted(set(reasons)),
        "checks": checks,
        "witness_sha256": baseline.get("witness_sha256"),
        "manifest_sha256": _hash(manifest),
        "filesystem_consistency_only": True,
        "hmac_cryptographically_verified": False,
        "field_identity_attested": False,
        "sensor_measurement_attested": False,
        "physical_hardware_qualified": False,
        "mesh_transport_verified": False,
        "action_authorized": False,
        "network_change_authorized": False,
        "rover_motion_authorized": False,
    }
    result["assessment_sha256"] = _hash(result)
    return result
