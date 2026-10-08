"""Offline, deterministic, non-actuating corridor/link assessment.

This module deliberately provides NO physical deployment, radio configuration,
network changes, autonomous movement, or remote control entrypoints.
Measurements are caller-supplied, untrusted, and never proof of coverage.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping, Sequence
from math import isfinite
import hashlib
import json


@dataclass(frozen=True)
class LinkObservation:
    parent: str
    child: str
    timestamp_s: float
    latency_ms: float
    loss_pct: float
    observed_mbps: float
    samples: int
    battery_pct: float | None = None
    # The string "measured" cannot be trusted as an attestation; source is metadata only.
    source: str = "unknown"


@dataclass(frozen=True)
class Thresholds:
    max_age_s: float = 90.0
    min_samples: int = 3
    max_latency_ms: float = 250.0
    max_loss_pct: float = 2.0
    min_observed_mbps: float = 1.0
    min_relay_battery_pct: float = 30.0


def _is_finite_number(value: Any) -> bool:
    return isinstance(value, (float, int)) and not isinstance(value, bool) and isfinite(float(value))


def _valid_thresholds(t: Thresholds) -> bool:
    nums = [t.max_age_s, t.max_latency_ms, t.max_loss_pct, t.min_observed_mbps, t.min_relay_battery_pct]
    return (all(_is_finite_number(v) for v in nums) and all(v >= 0 for v in nums)
            and 0 <= t.max_loss_pct <= 100 and 0 <= t.min_relay_battery_pct <= 100
            and isinstance(t.min_samples, int) and not isinstance(t.min_samples, bool)
            and t.min_samples >= 1)


def assess_corridor(
    path: Sequence[str],
    observations: Sequence[LinkObservation],
    *,
    now_s: float,
    thresholds: Thresholds | None = None,
    permission: Mapping[str, bool] | None = None,
    rover_health: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Assess one ordered gateway->relay(s)->rover path; returns recommendations only.

    `permission` values are input assertions, not authenticated approvals.
    `rover_health` expects a status packet's `last_decision`/`decision` with state.
    Only caller-side verified measurements/permission may be used for actual operations.
    """
    t = thresholds or Thresholds()
    reasons: list[str] = []
    warnings: list[str] = []
    hops: list[dict[str, Any]] = []
    if not _is_finite_number(now_s) or not _valid_thresholds(t):
        reasons.append("invalid_time_or_thresholds")
    if (not isinstance(path, (tuple, list)) or len(path) < 2
        or any(not isinstance(n, str) or not n.strip() for n in path)
        or len(path) != len(set(path))):
        reasons.append("invalid_path")
    # Exactly one unique observation per configured parent-child hop, no extra edges.
    expected = list(zip(path, path[1:])) if "invalid_path" not in reasons else []
    if not isinstance(observations, (tuple, list)):
        reasons.append("invalid_observations_container")
        observations = []
    if len(observations) != len(expected):
        reasons.append("observation_count_mismatch")
    by_edge: dict[tuple[str, str], LinkObservation] = {}
    for o in observations:
        if not isinstance(o, LinkObservation):
            reasons.append("invalid_observation_type")
            continue
        if not isinstance(o.parent, str) or not isinstance(o.child, str):
            reasons.append("invalid_link_identity")
            continue
        key = (o.parent, o.child)
        if key in by_edge:
            reasons.append("duplicate_link_observation")
        by_edge[key] = o
    if set(by_edge) != set(expected):
        reasons.append("topology_mismatch")
    if not reasons:
        for parent, child in expected:
            o = by_edge[(parent, child)]
            issues: list[str] = []
            numeric = [o.timestamp_s, o.latency_ms, o.loss_pct, o.observed_mbps]
            if o.battery_pct is not None:
                numeric.append(o.battery_pct)
            if not all(_is_finite_number(x) for x in numeric):
                issues.append("nonfinite_measurement")
            else:
                age = float(now_s) - float(o.timestamp_s)
                if age < 0 or age > t.max_age_s:
                    issues.append("stale_or_future_reading")
                if o.latency_ms < 0 or o.latency_ms > t.max_latency_ms:
                    issues.append("latency_out_of_bounds")
                if not 0 <= o.loss_pct <= 100 or o.loss_pct > t.max_loss_pct:
                    issues.append("loss_out_of_bounds")
                if o.observed_mbps < t.min_observed_mbps:
                    issues.append("low_observed_throughput")
                if o.battery_pct is not None and not 0 <= o.battery_pct <= 100:
                    issues.append("invalid_battery_pct")
                if child != path[-1] and o.battery_pct is None:
                    issues.append("relay_battery_unknown")
                elif child != path[-1] and o.battery_pct < t.min_relay_battery_pct:
                    issues.append("relay_battery_low")
            if not isinstance(o.samples, int) or isinstance(o.samples, bool) or o.samples < t.min_samples:
                issues.append("insufficient_samples")
            hops.append({"parent": parent, "child": child, "issues": issues,
                         "latency_ms": o.latency_ms if _is_finite_number(o.latency_ms) else None,
                         "loss_pct": o.loss_pct if _is_finite_number(o.loss_pct) else None,
                         "observed_mbps": o.observed_mbps if _is_finite_number(o.observed_mbps) else None,
                         "source": o.source if isinstance(o.source, str) else "invalid"})
            reasons.extend(f"{parent}->{child}:{issue}" for issue in issues)
    # Rover packet is advisory health evidence, not movement authority.
    if rover_health is None:
        warnings.append("rover_health_packet_not_supplied")
    else:
        decision = rover_health.get("last_decision", rover_health.get("decision", {})) if isinstance(rover_health, Mapping) else {}
        state = decision.get("state") if isinstance(decision, Mapping) else None
        if state not in {"BEACON_READY", "TELEMETRY_READY", "REMOTE_MONITOR_READY"}:
            reasons.append("rover_health_not_ready_or_unrecognized")
        boundary = rover_health.get("claim_boundary", {}) if isinstance(rover_health, Mapping) else {}
        if not isinstance(boundary, Mapping) or boundary.get("does_not_grant_motion_authority") is not True:
            reasons.append("rover_claim_boundary_missing_or_inconsistent")
    p = permission if isinstance(permission, Mapping) else {}
    if not p.get("operator_present", False):
        reasons.append("operator_presence_unconfirmed")
    if not p.get("site_permission", False):
        reasons.append("site_permission_unconfirmed")

    # This package never grants authority. Positive status means *review* only.
    state = "REVIEW_CANDIDATE" if not reasons else "HOLD"
    result = {
        "schema": "phipie.trail.corridor.assessment.v0.1",
        "state": state,
        "path": list(path) if isinstance(path, (tuple, list)) and all(isinstance(x, str) for x in path) else [],
        "hops": hops,
        "reasons": sorted(set(reasons)),
        "warnings": warnings,
        "recommendation": ("Continue operator-supervised survey; human review required before any physical deployment"
                           if state == "REVIEW_CANDIDATE" else
                           "Hold proposed extension; inspect evidence and preserve the last independently verified route"),
        "estimated_path_latency_ms": round(sum(h["latency_ms"] for h in hops), 3) if hops and not reasons else None,
        "link_throughput_floor_mbps": min((h["observed_mbps"] for h in hops), default=None) if not reasons else None,
        "physical_deployment_authorized": False,
        "rover_motion_authorized": False,
        "network_config_change_authorized": False,
        "authenticated_end_to_end_proof": False,
        "note": "Diagnostic proxies, not measured end-to-end availability, capacity, or cryptographic attestation",
    }
    # A checksum detects incidental packet changes but does not authenticate its source.
    stable = json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False)
    result["checksum_sha256"] = hashlib.sha256(stable.encode("utf-8")).hexdigest()
    return result
