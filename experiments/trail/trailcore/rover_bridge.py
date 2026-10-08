"""Read-only parser for Park Rover v6.7 telemetry_mesh_packet exports.

The archived checksum is not a digital signature or origin authentication.
Supply only packets from independently authenticated Rover connections.
"""
from __future__ import annotations
from typing import Any, Mapping
import hashlib
import json
from math import isfinite


def normalized_rover_health(packet: Any, *, now_s: float, max_age_s: float = 90.0) -> dict[str, Any]:
    """Reject invalid/stale/tampered *checksummed* beacon packets; never grant motion.

    Output is a minimal status for assess_corridor(rover_health=...), *not* authorization.
    """
    denied = {
        "last_decision": {"state": "BRIDGE_REJECTED"},
        "claim_boundary": {"does_not_grant_motion_authority": True},
        "bridge_authenticated": False,
    }
    if not isinstance(packet, Mapping) or packet.get("bundle_type") != "telemetry_mesh_packet" or str(packet.get("version")) != "6.7":
        return {**denied, "bridge_reason": "invalid_packet_version_or_type"}
    ts = packet.get("created_ts")
    if (not isinstance(ts, (int, float)) or isinstance(ts, bool) or not isfinite(float(ts))
        or not isinstance(now_s, (int, float)) or isinstance(now_s, bool) or not isfinite(float(now_s))
        or not isinstance(max_age_s, (int, float)) or not isfinite(float(max_age_s)) or max_age_s < 0
        or now_s < ts or now_s - ts > max_age_s):
        return {**denied, "bridge_reason": "invalid_or_stale_timestamp"}
    provided = packet.get("telemetry_mesh_packet_hash")
    try:
        canonical = json.dumps({k: v for k, v in packet.items() if k not in {"created_ts", "telemetry_mesh_packet_hash"}},
                               sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        calculated = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    except (TypeError, ValueError):
        return {**denied, "bridge_reason": "nonserializable_packet"}
    if not isinstance(provided, str) or len(provided) != 64 or provided != calculated:
        return {**denied, "bridge_reason": "packet_checksum_mismatch"}
    boundary = packet.get("claim_boundary")
    dec = packet.get("decision")
    if not isinstance(boundary, Mapping) or not isinstance(dec, Mapping):
        return {**denied, "bridge_reason": "missing_safety_claims"}
    if boundary.get("does_not_grant_motion_authority") is not True or boundary.get("does_not_allow_remote_drive") is not True:
        return {**denied, "bridge_reason": "unsafe_safety_claims"}
    state = dec.get("state")
    if not isinstance(state, str):
        return {**denied, "bridge_reason": "invalid_rover_state"}
    return {
        "last_decision": {"state": state},
        "claim_boundary": {"does_not_grant_motion_authority": True},
        "bridge_authenticated": False,
        "bridge_reason": "checksum_valid_origin_unverified",
    }
