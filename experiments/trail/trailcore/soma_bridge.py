"""Narrow SOMA-to-ΦTrail seam. Only successful in-process HMAC intake yields a link.

The returned LinkObservation is still an advisory measurement, not a proven
end-to-end route or authorization to run the network or move the rover.
"""
from __future__ import annotations
from typing import Any
from .governor import LinkObservation
from .soma_observation import SomaIntake


def admit_network_link(intake: SomaIntake, packet: Any, *, now_s: float) -> dict:
    admitted = intake.receive(packet, now_s=now_s)
    if admitted["status"] != "ACCEPTED_ADVISORY_ONLY":
        return {"status": "HOLD", "reason": admitted["reason"], "link": None, "receipt": None}
    observation = admitted["observation"]
    if observation["organ"] != "sense.network":
        return {"status": "HOLD", "reason": "NOT_NETWORK_ORGAN", "link": None,
                "receipt": admitted["receipt"]}
    m = observation["measurement"]
    link = LinkObservation(
        parent=m["parent_id"], child=m["child_id"], timestamp_s=observation["observed_at_s"],
        latency_ms=m["latency_ms"], loss_pct=m["loss_pct"],
        observed_mbps=m["observed_mbps"], samples=m["sample_count"],
        battery_pct=None,
        source="phipie.soma.hmac-lab-advisory-v0.1",
    )
    return {"status": "OBSERVED_ADVISORY_ONLY", "reason": None,
            "link": link, "receipt": admitted["receipt"]}
