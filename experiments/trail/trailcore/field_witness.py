"""PhiPie Trail field witness v0.1.

Manual and machine-readable evidence inventory for two physically separate Pi
tests. An operator's assertions are NOT hardware attestation or proof of coverage.
Never stores credentials, MAC/SSID, GPS, photos, or shell output.
"""
from __future__ import annotations

from hashlib import sha256
import json
import math
import re
from typing import Any

INPUT_CONTRACT = "phipie-trail-field-witness-input/v0.1"
RESULT_CONTRACT = "phipie-trail-field-witness-assessment/v0.1"
TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")
HEX = re.compile(r"^[a-f0-9]{64}$")
ROLES = {"sender", "receiver"}
MODES = {"LAB_SIMULATION", "OPERATOR_FIELD"}
CLOCK_METHODS = {"UNKNOWN", "NTP_OBSERVED", "GPS_CLOCK_OBSERVED", "MANUAL_OBSERVED"}
PLATFORMS = {"RPI5_REPORTED", "CM5_REPORTED", "LINUX_OTHER", "UNKNOWN"}


def _is_bool(x: Any) -> bool:
    return type(x) is bool


def _num(x: Any, lo: float, hi: float) -> bool:
    if type(x) not in (int, float):
        return False
    try:
        return math.isfinite(x) and lo <= x <= hi
    except (TypeError, OverflowError, ValueError):
        return False


def _token(x: Any) -> bool:
    return isinstance(x, str) and TOKEN.fullmatch(x) is not None


def _digest(x: Any) -> bool:
    return isinstance(x, str) and HEX.fullmatch(x) is not None


def _shape(x: Any, keys: set[str]) -> bool:
    return type(x) is dict and set(x) == keys


def template() -> dict[str, Any]:
    """All evidence defaults UNKNOWN/missing; never populate a synthetic PASS."""
    return {
        "schema": INPUT_CONTRACT,
        "test_id": "trial-001",
        "mode": "OPERATOR_FIELD",
        "site_authorized": False,
        "operator_present": False,
        "nodes": [
            {"role": "sender", "node_id": "relay-a",
             "platform": "UNKNOWN", "evidence_origin": "UNKNOWN",
             "host_snapshot_sha256": None, "radio_report_sha256": None,
             "boot_session_observed": False},
            {"role": "receiver", "node_id": "base-b",
             "platform": "UNKNOWN", "evidence_origin": "UNKNOWN",
             "host_snapshot_sha256": None, "radio_report_sha256": None,
             "boot_session_observed": False},
        ],
        "handoff": {
            "manual_transfer_observed": False,
            "packet_sha256": None,
            "receive_receipt_sha256": None,
            "accepted_advisory_only": False,
            "replay_refused_after_restart": False,
            "tamper_refused": False,
            "clock_method": "UNKNOWN",
            "clock_skew_ms": None,
        },
        "path_test": {
            "independent_test_run": False,
            "kind": "NONE",
            "evidence_sha256": None,
            "packet_loss_pct": None,
            "rtt_avg_ms": None,
            "throughput_mbps": None,
        },
        "safety": {
            "no_network_writes_observed": False,
            "no_rover_motion_observed": False,
            "no_relay_deployment_observed": False,
        },
    }


def assess_witness(witness: Any) -> dict[str, Any]:
    """Only HOLD or OPERATOR_REVIEW_CANDIDATE; never physical qualification."""
    reasons: list[str] = []
    schema_ok = _shape(witness, set(template()))
    if not schema_ok:
        return _result("HOLD", ["INVALID_TOP_LEVEL_SHAPE"])
    if witness["schema"] != INPUT_CONTRACT:
        reasons.append("INPUT_CONTRACT_MISMATCH")
    if not _token(witness["test_id"]):
        reasons.append("INVALID_TEST_ID")
    if not isinstance(witness["mode"], str) or witness["mode"] not in MODES:
        reasons.append("INVALID_MODE")
    if not _is_bool(witness["site_authorized"]) or witness["site_authorized"] is not True:
        reasons.append("SITE_AUTHORIZATION_UNCONFIRMED")
    if not _is_bool(witness["operator_present"]) or witness["operator_present"] is not True:
        reasons.append("OPERATOR_ABSENT")
    nodes = witness["nodes"]
    if not isinstance(nodes, list) or len(nodes) != 2:
        reasons.append("TWO_NODE_EVIDENCE_REQUIRED")
    else:
        seen_roles: set[str] = set()
        seen_nodes: set[str] = set()
        expected_node = set(template()["nodes"][0])
        for node in nodes:
            if not _shape(node, expected_node):
                reasons.append("INVALID_NODE_SHAPE")
                continue
            if not isinstance(node["role"], str) or node["role"] not in ROLES or node["role"] in seen_roles:
                reasons.append("DUPLICATE_OR_INVALID_ROLE")
            else:
                seen_roles.add(node["role"])
            if not _token(node["node_id"]) or node["node_id"] in seen_nodes:
                reasons.append("DUPLICATE_OR_INVALID_NODE")
            else:
                seen_nodes.add(node["node_id"])
            if not isinstance(node["platform"], str) or node["platform"] not in PLATFORMS:
                reasons.append("INVALID_PLATFORM")
            if not isinstance(node["evidence_origin"], str) or node["evidence_origin"] not in {"LOCAL_LINUX", "SYNTHETIC", "UNKNOWN"}:
                reasons.append("INVALID_EVIDENCE_ORIGIN")
            if not _digest(node["host_snapshot_sha256"]) or not _digest(node["radio_report_sha256"]):
                reasons.append("MISSING_DEVICE_EVIDENCE")
            if node["boot_session_observed"] is not True:
                reasons.append("BOOT_SESSION_UNCONFIRMED")
        if seen_roles != ROLES:
            reasons.append("SENDER_RECEIVER_ROLES_REQUIRED")
    handoff = witness["handoff"]
    if not _shape(handoff, set(template()["handoff"])):
        reasons.append("INVALID_HANDOFF_SHAPE")
    else:
        for key in ("manual_transfer_observed", "accepted_advisory_only",
                    "replay_refused_after_restart", "tamper_refused"):
            if handoff[key] is not True:
                reasons.append("HANDOFF_" + key.upper() + "_MISSING")
        for key in ("packet_sha256", "receive_receipt_sha256"):
            if not _digest(handoff[key]):
                reasons.append("HANDOFF_" + key.upper() + "_MISSING")
        if not isinstance(handoff["clock_method"], str) or handoff["clock_method"] not in CLOCK_METHODS:
            reasons.append("INVALID_CLOCK_METHOD")
        if handoff["clock_method"] == "UNKNOWN" or not _num(handoff["clock_skew_ms"], 0, 90_000):
            reasons.append("CLOCK_EVIDENCE_INCOMPLETE")
    path = witness["path_test"]
    if not _shape(path, set(template()["path_test"])):
        reasons.append("INVALID_PATH_TEST_SHAPE")
    else:
        if path["independent_test_run"] is not True or not isinstance(path["kind"], str) or path["kind"] not in {"ICMP", "TCP_BENCHMARK"}:
            reasons.append("INDEPENDENT_PATH_TEST_MISSING")
        if not _digest(path["evidence_sha256"]):
            reasons.append("PATH_EVIDENCE_MISSING")
        if not _num(path["packet_loss_pct"], 0, 100):
            reasons.append("PATH_LOSS_INVALID")
        if not _num(path["rtt_avg_ms"], 0, 60_000):
            reasons.append("PATH_RTT_INVALID")
        if path["kind"] == "TCP_BENCHMARK" and not _num(path["throughput_mbps"], 0, 100_000):
            reasons.append("THROUGHPUT_EVIDENCE_MISSING")
        if path["kind"] == "ICMP" and path["throughput_mbps"] is not None:
            reasons.append("ICMP_THROUGHPUT_MUST_BE_UNKNOWN")
    safety = witness["safety"]
    if not _shape(safety, set(template()["safety"])):
        reasons.append("INVALID_SAFETY_SHAPE")
    elif any(v is not True for v in safety.values()):
        reasons.append("SAFETY_WITNESS_INCOMPLETE")
    if witness["mode"] == "LAB_SIMULATION":
        reasons.append("SIMULATION_CANNOT_QUALIFY_FIELD")
    if isinstance(nodes, list):
        for n in nodes:
            if isinstance(n, dict) and (n.get("evidence_origin") != "LOCAL_LINUX"
               or n.get("platform") not in {"RPI5_REPORTED", "CM5_REPORTED"}):
                reasons.append("PHYSICAL_PI_OBSERVATION_MISSING")
    return _result(
        "OPERATOR_REVIEW_CANDIDATE" if not reasons else "HOLD",
        sorted(set(reasons)),
        test_id=witness["test_id"] if _token(witness["test_id"]) else None,
        witness_digest=_hash(witness),
    )


def _hash(value: Any) -> str | None:
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, OverflowError):
        return None
    return sha256(raw).hexdigest()


def _result(status: str, reasons: list[str], test_id: str | None = None,
            witness_digest: str | None = None) -> dict[str, Any]:
    result = {
        "contract": RESULT_CONTRACT,
        "status": status,
        "reasons": reasons,
        "test_id": test_id,
        "witness_sha256": witness_digest,
        "operator_claims_only": True,
        "hardware_physically_qualified": False,
        "mesh_transport_verified": False,
        "emergency_coverage_verified": False,
        "action_authorized": False,
        "network_change_authorized": False,
        "rover_motion_authorized": False,
        "soma_runtime_wired": False,
        "note": "Review of bounded operator-supplied assertions; evidence hash is not attestation",
    }
    result["assessment_sha256"] = _hash(result)
    return result
