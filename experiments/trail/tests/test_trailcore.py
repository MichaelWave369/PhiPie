import unittest
from dataclasses import replace
from trailcore.demo import run
from trailcore.governor import assess_corridor, LinkObservation, Thresholds


class TrailCoreTests(unittest.TestCase):
    def test_nominal_is_review_only(self):
        a = run("nominal")
        self.assertEqual(a["state"], "REVIEW_CANDIDATE")
        self.assertFalse(a["physical_deployment_authorized"])
        self.assertFalse(a["rover_motion_authorized"])
        self.assertFalse(a["network_config_change_authorized"])
        self.assertFalse(a["authenticated_end_to_end_proof"])
        self.assertEqual(len(a["hops"]), 3)

    def test_degraded_holds(self):
        a = run("degraded")
        self.assertEqual(a["state"], "HOLD")
        self.assertIn("relay-a->relay-b:loss_out_of_bounds", a["reasons"])

    def test_stale_holds(self):
        self.assertIn("relay-a->relay-b:stale_or_future_reading", run("stale")["reasons"])

    def test_missing_readings_hold(self):
        a = assess_corridor(["base", "relay"], [], now_s=1000, permission={})
        self.assertEqual(a["state"], "HOLD")

    def test_topology_cycle_holds(self):
        a = assess_corridor(["base", "base"], [], now_s=1000)
        self.assertEqual(a["state"], "HOLD")

    def test_missing_permissions_hold(self):
        a = assess_corridor(["base", "rover"], [LinkObservation("base", "rover", 999, 25, 0, 12, 4)], now_s=1000)
        self.assertEqual(a["state"], "HOLD")

    def test_missing_relay_battery_holds(self):
        a = assess_corridor(["base", "relay", "rover"], [
            LinkObservation("base", "relay", 999, 25, 0, 12, 4),
            LinkObservation("relay", "rover", 999, 25, 0, 12, 4)], now_s=1000,
            permission={"operator_present": True, "site_permission": True},
            rover_health={"last_decision": {"state": "BEACON_READY"},
                          "claim_boundary": {"does_not_grant_motion_authority": True}})
        self.assertIn("base->relay:relay_battery_unknown", a["reasons"])

    def test_duplicate_edge_blocks(self):
        l = LinkObservation("base", "rover", 999, 25, 0, 12, 4)
        a = assess_corridor(["base", "rover"], [l, l], now_s=1000)
        self.assertEqual(a["state"], "HOLD")

    def test_bad_rover_packet_blocks(self):
        l = LinkObservation("base", "rover", 999, 25, 0, 12, 4)
        a = assess_corridor(["base", "rover"], [l], now_s=1000,
            permission={"operator_present": True, "site_permission": True},
            rover_health={"last_decision": {"state": "MESH_BLOCKED"}})
        self.assertIn("rover_health_not_ready_or_unrecognized", a["reasons"])

    def test_future_and_nan_blocks(self):
        l = LinkObservation("base", "rover", 1001, 25, 0, 12, 4)
        a = assess_corridor(["base", "rover"], [l], now_s=1000)
        self.assertIn("base->rover:stale_or_future_reading", a["reasons"])
        l2 = replace(l, timestamp_s=999, latency_ms=float("nan"))
        a2 = assess_corridor(["base", "rover"], [l2], now_s=1000)
        self.assertIn("base->rover:nonfinite_measurement", a2["reasons"])

    def test_bad_link_identity_and_container_holds(self):
        bad = LinkObservation({"invalid": "node"}, "rover", 999, 25, 0, 12, 4)
        self.assertEqual(assess_corridor(["base", "rover"], [bad], now_s=1000)["state"], "HOLD")
        self.assertEqual(assess_corridor(["base", "rover"], None, now_s=1000)["state"], "HOLD")

    def test_deterministic_checksum(self):
        self.assertEqual(run("nominal")["checksum_sha256"], run("nominal")["checksum_sha256"])

    def test_invalid_threshold_holds(self):
        a = assess_corridor(["base", "rover"], [LinkObservation("base", "rover", 999, 25, 0, 12, 4)], now_s=1000,
            thresholds=Thresholds(min_samples=0))
        self.assertEqual(a["state"], "HOLD")
