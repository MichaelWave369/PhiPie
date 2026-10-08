"""Pure offline SOMA sensor -> advisory corridor path. Synthetic readings only.

Run: python -m trailcore.soma_demo
"""
from __future__ import annotations
import copy
import hmac
import json

from .governor import assess_corridor
from .soma_bridge import admit_network_link
from .soma_observation import AUTHORITY, CONTRACT, KeyBinding, SomaIntake, canonical_json


def run_demo():
    # Test-only key, never a shipped field credential. No network or hardware.
    lab_secret = bytes(range(32))
    intake = SomaIntake({"demo-key": KeyBinding("lab", "rover", lab_secret)})
    packet = {
        "contract": CONTRACT,
        "site_id": "lab", "node_id": "rover",
        "observation_id": "observation-1",
        "organ": "sense.network", "observed_at_s": 1000.0,
        "sequence": 1,
        "measurement": {
            "parent_id": "base", "child_id": "rover",
            "latency_ms": 30.0, "loss_pct": 0.2,
            "observed_mbps": 12.0, "sample_count": 5,
        },
        "authority": copy.deepcopy(AUTHORITY),
    }
    mac = hmac.new(lab_secret, canonical_json(packet), "sha256").hexdigest()
    packet["signature"] = {"alg": "HMAC-SHA256", "key_id": "demo-key", "mac_hex": mac}
    received = admit_network_link(intake, packet, now_s=1001.0)
    assert received["status"] == "OBSERVED_ADVISORY_ONLY"
    report = assess_corridor(
        ["base", "rover"], [received["link"]], now_s=1001.0,
        # These are lab claims, NOT authenticated operator authority.
        permission={"operator_present": True, "site_permission": True},
        rover_health={"last_decision": {"state": "BEACON_READY"},
                      "claim_boundary": {"does_not_grant_motion_authority": True}},
    )
    return {"receipt": received["receipt"], "corridor": report,
            "mode": "OFFLINE_SYNTHETIC_READ_ONLY"}


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2))
