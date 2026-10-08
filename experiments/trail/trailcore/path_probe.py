"""ΦTrail bounded ICMP field-probe evidence v0.1.

One explicitly operator-approved ping on an owned/private network; emits two
PRIVATE local JSON files: underlying parsed observation and legacy-compatible
path summary. No automatically running service, streaming or radio reconfig.
Neither file is physical, peer, route, or command authority.
"""
from __future__ import annotations

from typing import Any
from .evidence_binding import PATH_CONTRACT
from .linux_radio import observe_ping

ORIGIN = "OPERATOR_RECORDED_INDEPENDENT"  # legacy summary; raw probe is checked separately


def collect_icmp_pair(target: str, interface: str, *, approved: bool,
                      runner: Any = None) -> dict[str, Any]:
    """No wire traffic unless approved; unknown/failed evidence is a HOLD."""
    probe = observe_ping(target, interface, approved=approved, runner=runner)
    if probe["status"] != "OBSERVED_ADVISORY_ONLY":
        return {
            "status": "HOLD", "reason": probe["reason"],
            "probe": None, "path_record": None,
            "network_change_authorized": False, "rover_motion_authorized": False,
        }
    m = probe["metrics"]
    path = {
        "schema": PATH_CONTRACT,
        "kind": "ICMP",
        "packet_loss_pct": m["probe_packet_loss_pct"],
        "rtt_avg_ms": m["probe_rtt_avg_ms"],
        "throughput_mbps": None,
        "independent_test_run": True,
        "evidence_origin": ORIGIN,
    }
    return {
        "status": "LOCAL_PROBE_OBSERVED",
        "reason": None,
        "probe": probe,
        "path_record": path,
        "network_change_authorized": False,
        "rover_motion_authorized": False,
    }
