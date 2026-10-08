import hashlib
import json
import unittest
from trailcore.rover_bridge import normalized_rover_health


def example_packet(ts=1000.0):
    packet = {
        "bundle_type": "telemetry_mesh_packet",
        "version": "6.7",
        "created_ts": ts,
        "decision": {"state": "BEACON_READY"},
        "claim_boundary": {
            "does_not_grant_motion_authority": True,
            "does_not_allow_remote_drive": True,
        },
    }
    canonical = json.dumps(
        {k: v for k, v in packet.items() if k not in {"created_ts", "telemetry_mesh_packet_hash"}},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
    )
    packet["telemetry_mesh_packet_hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return packet


class RoverBridgeTests(unittest.TestCase):
    def test_valid_checksum_still_not_authenticated(self):
        result = normalized_rover_health(example_packet(), now_s=1001.0)
        self.assertEqual(result["last_decision"]["state"], "BEACON_READY")
        self.assertFalse(result["bridge_authenticated"])
        self.assertTrue(result["claim_boundary"]["does_not_grant_motion_authority"])

    def test_tampering_rejected(self):
        packet = example_packet()
        packet["decision"]["state"] = "BEACON_READY_HACKED"
        result = normalized_rover_health(packet, now_s=1001.0)
        self.assertEqual(result["bridge_reason"], "packet_checksum_mismatch")

    def test_stale_rejected(self):
        result = normalized_rover_health(example_packet(), now_s=2000.0)
        self.assertEqual(result["last_decision"]["state"], "BRIDGE_REJECTED")

    def test_invalid_packet_rejected(self):
        result = normalized_rover_health({"arbitrary": True}, now_s=1001.0)
        self.assertEqual(result["last_decision"]["state"], "BRIDGE_REJECTED")
