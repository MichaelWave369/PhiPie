"""PhiCluster read-only scheduling advisor, v0.1.

Experimental synthetic-data planning only. No network, GPIO, dispatch, battery
switching, or physical power control. This module does not grant authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "phicluster-synthetic/v0.1"
MAX_TELEMETRY_AGE_SECONDS = 120
PRIORITIES = {"essential": 0, "standard": 1, "opportunistic": 2}
ROLES = {"control", "service", "vault", "mesh", "sense", "agent", "xr-link"}
ZERO_HASH = "0" * 64


class ContractError(ValueError):
    """Malformed or untrustworthy scenario. No recommendations are emitted."""


def _obj(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{name} must be an object")
    return value


def _keys(value: dict[str, Any], name: str, fields: set[str]) -> None:
    missing = fields - set(value)
    extra = set(value) - fields
    if missing or extra:
        raise ContractError(
            f"{name} keys mismatch: missing={sorted(missing)}, extra={sorted(extra)}"
        )


def _number(value: Any, name: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f"{name} must be numeric")
    number = float(value)
    if not math.isfinite(number) or not minimum <= number <= maximum:
        raise ContractError(f"{name} outside finite [{minimum}, {maximum}]")
    return number


def _integer(value: Any, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise ContractError(f"{name} outside [{minimum}, {maximum}]")
    return value


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 128:
        raise ContractError(f"{name} must be a nonempty string <= 128 chars")
    return value


def utc_time(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ContractError("timestamps must use explicit UTC Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ContractError("invalid UTC timestamp") from exc
    if parsed.utcoffset().total_seconds() != 0:
        raise ContractError("timestamp must be UTC")
    return parsed


def _validate(payload: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    _keys(payload, "scenario", {"schema", "power", "nodes", "jobs"})
    if payload["schema"] != SCHEMA:
        raise ContractError(f"scenario must use {SCHEMA}")

    power = _obj(payload["power"], "power")
    _keys(
        power,
        "power",
        {
            "observed_at", "source", "supply_mode", "solar_w",
            "battery_soc_pct", "battery_health", "safe_incremental_w",
        },
    )
    utc_time(power["observed_at"])
    if power["source"] != "synthetic":
        raise ContractError("v0.1 accepts synthetic telemetry only")
    if power["supply_mode"] not in {"solar-battery", "battery", "mains", "unknown"}:
        raise ContractError("unrecognized supply_mode")
    _number(power["solar_w"], "solar_w", 0, 100000)
    _number(power["battery_soc_pct"], "battery_soc_pct", 0, 100)
    _number(power["safe_incremental_w"], "safe_incremental_w", 0, 10000)
    if power["battery_health"] not in {"ok", "fault", "unknown"}:
        raise ContractError("unrecognized battery_health")

    nodes = payload["nodes"]
    jobs = payload["jobs"]
    if not isinstance(nodes, list) or not 1 <= len(nodes) <= 128:
        raise ContractError("nodes must be a list of 1..128 entries")
    if not isinstance(jobs, list) or len(jobs) > 1000:
        raise ContractError("jobs must be a list of at most 1000 entries")

    seen_nodes: set[str] = set()
    for i, node in enumerate(nodes):
        _obj(node, f"nodes[{i}]")
        _keys(node, f"nodes[{i}]", {"node_id", "role", "state", "max_incremental_w", "free_slots"})
        node_id = _text(node["node_id"], "node_id")
        if node_id in seen_nodes:
            raise ContractError("duplicate node_id")
        seen_nodes.add(node_id)
        if node["role"] not in ROLES:
            raise ContractError("unsupported node role")
        if node["state"] not in {"ready", "offline", "fault"}:
            raise ContractError("unsupported node state")
        _number(node["max_incremental_w"], "max_incremental_w", 0, 10000)
        _integer(node["free_slots"], "free_slots", 0, 1000)

    seen_jobs: set[str] = set()
    for i, job in enumerate(jobs):
        _obj(job, f"jobs[{i}]")
        _keys(
            job, f"jobs[{i}]",
            {"job_id", "required_role", "priority", "incremental_w", "simulated_grant"},
        )
        job_id = _text(job["job_id"], "job_id")
        if job_id in seen_jobs:
            raise ContractError("duplicate job_id")
        seen_jobs.add(job_id)
        if job["required_role"] not in ROLES:
            raise ContractError("unsupported required_role")
        if job["priority"] not in PRIORITIES:
            raise ContractError("unsupported priority")
        _number(job["incremental_w"], "incremental_w", 0.01, 10000)
        if type(job["simulated_grant"]) is not bool:
            raise ContractError("simulated_grant must be boolean")

    return power, nodes, jobs


def advise(payload: dict[str, Any], *, now: datetime) -> dict[str, Any]:
    """Return deterministic dry-run placements and hash-linked advisory receipts.

    The simulated_grant flag is NOT a verified PhiOS authority grant. Production
    execution requires separate authentication, governance, and safety checks.
    """
    _obj(payload, "scenario")
    if now.tzinfo is None or now.utcoffset().total_seconds() != 0:
        raise ContractError("now must be timezone-aware UTC")
    power, nodes, jobs = _validate(payload)

    age_seconds = (now - utc_time(power["observed_at"])).total_seconds()
    stale = not -5 <= age_seconds <= MAX_TELEMETRY_AGE_SECONDS
    health_ok = power["battery_health"] == "ok"
    soc = float(power["battery_soc_pct"])
    if stale or not health_ok:
        mode = "untrusted"
    elif soc < 20:
        mode = "critical"
    elif soc < 45:
        mode = "conservation"
    else:
        mode = "normal"

    budget = float(power["safe_incremental_w"])
    budget_used = 0.0
    slots_used = {node["node_id"]: 0 for node in nodes}
    watts_used = {node["node_id"]: 0.0 for node in nodes}
    decisions: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
    previous_hash = ZERO_HASH

    for job in sorted(jobs, key=lambda j: (PRIORITIES[j["priority"]], j["job_id"])):
        requested_w = float(job["incremental_w"])
        node_id: str | None = None
        outcome, reason = "defer", "no qualifying node or power budget"
        if not job["simulated_grant"]:
            outcome, reason = "deny", "synthetic permission flag absent (not a real grant)"
        elif stale:
            reason = "power telemetry stale or future-dated"
        elif not health_ok:
            reason = "battery health fault or unknown"
        elif mode == "critical":
            reason = "battery reserve critical; no new placements"
        elif mode == "conservation" and job["priority"] != "essential":
            reason = "conservation admits essential jobs only"
        elif requested_w + budget_used > budget + 1e-9:
            reason = "incremental site power budget exceeded"
        else:
            candidates = sorted(
                (
                    node for node in nodes
                    if node["role"] == job["required_role"]
                    and node["state"] == "ready"
                    and slots_used[node["node_id"]] < node["free_slots"]
                    and watts_used[node["node_id"]] + requested_w
                    <= float(node["max_incremental_w"]) + 1e-9
                ),
                key=lambda node: node["node_id"],
            )
            if candidates:
                node_id = candidates[0]["node_id"]
                slots_used[node_id] += 1
                watts_used[node_id] += requested_w
                budget_used += requested_w
                outcome, reason = "propose", "fits synthetic budget and role"
        decision = {
            "job_id": job["job_id"],
            "decision": outcome,
            "reason": reason,
            "proposed_node_id": node_id,
            "incremental_w": requested_w if outcome == "propose" else 0.0,
            "action_executed": False,
        }
        decisions.append(decision)
        body = {
            "schema": "phicluster-advisory-receipt/v0.1",
            "dry_run": True,
            "decision": decision,
            "previous_hash": previous_hash,
        }
        digest = hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        receipts.append({**body, "current_hash": digest})
        previous_hash = digest

    return {
        "schema": "phicluster-advice/v0.1",
        "simulation_only": True,
        "no_execution": True,
        "qualifies_hardware": False,
        "power_mode": mode,
        "telemetry_age_seconds": age_seconds,
        "incremental_budget_w": budget,
        "proposed_incremental_w": round(budget_used, 3),
        "decisions": decisions,
        "receipts": receipts,
        "receipt_head": previous_hash,
    }


def _reject_nonstandard_json(value: str) -> None:
    raise ContractError(f"nonstandard JSON numeric constant: {value}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", type=Path, help="Local synthetic scenario JSON")
    parser.add_argument(
        "--now", help="UTC simulation clock in ISO-8601 Z; default real UTC"
    )
    args = parser.parse_args()
    try:
        payload = json.loads(
            args.scenario.read_text(encoding="utf-8"),
            parse_constant=_reject_nonstandard_json,
        )
        result = advise(payload, now=utc_time(args.now) if args.now else datetime.now(timezone.utc))
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    except (ContractError, OSError, json.JSONDecodeError) as exc:
        parser.exit(2, f"scenario refused: {exc}\n")


if __name__ == "__main__":
    main()
