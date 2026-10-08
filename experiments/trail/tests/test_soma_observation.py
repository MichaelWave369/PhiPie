"""Adversarial offline acceptance for ΦTrail × SOMA advisory observation."""
import copy
import hmac
import json
import math
import unittest
from pathlib import Path

from trailcore.governor import assess_corridor
from trailcore.soma_bridge import admit_network_link
from trailcore.soma_demo import run_demo
from trailcore.soma_observation import (
    AUTHORITY, CONTRACT, KeyBinding, ReplayWindow, SomaIntake,
    canonical_json, ORGANS,
)

SECRET = bytes(range(32))


def make_packet(organ="sense.network", sequence=1, node="rover", **overrides):
    observations = {
        "sense.network": dict(parent_id="base", child_id=node, latency_ms=30,
                              loss_pct=0.2, observed_mbps=12, sample_count=5),
        "sense.radio": dict(peer_id="base", rssi_dbm=-59,
                            retry_pct=2, sample_count=8),
        "sense.power": dict(battery_pct=89, supply_mv=5000, cpu_temp_c=39),
        "sense.environment": dict(temperature_c=21, relative_humidity_pct=43),
        "sense.location": dict(zone_id="zone-a", confidence=0.8),
        "eyes.rover": dict(frame_sha256="a" * 64, media_type="image/jpeg",
                           width_px=640, height_px=480, capture_scope="operator_once"),
    }
    packet = {
        "contract": CONTRACT, "site_id": "lab", "node_id": node,
        "observation_id": f"obs-{sequence}", "organ": organ,
        "observed_at_s": 1000.0, "sequence": sequence,
        "measurement": observations[organ], "authority": copy.deepcopy(AUTHORITY),
    }
    packet.update(overrides)
    return sign(packet)


def sign(packet, secret=SECRET, key_id="lab-rover-1"):
    unsigned = {k: v for k, v in packet.items() if k != "signature"}
    packet["signature"] = {
        "alg": "HMAC-SHA256", "key_id": key_id,
        "mac_hex": hmac.new(secret, canonical_json(unsigned), "sha256").hexdigest(),
    }
    return packet


def intake(window=None):
    return SomaIntake({"lab-rover-1": KeyBinding("lab", "rover", SECRET)}, replay=window)


class SomaObservationTests(unittest.TestCase):
    def test_all_six_organs_are_read_only(self):
        for organ in ORGANS:
            with self.subTest(organ=organ):
                p = make_packet(organ)
                r = intake().receive(p, now_s=1001)
                self.assertEqual(r["status"], "ACCEPTED_ADVISORY_ONLY")
                self.assertEqual(r["receipt"]["type"], "ObservationReceipt")
                self.assertFalse(r["authorityGranted"])
                self.assertFalse(r["hardwareCommandAllowed"])
                self.assertFalse(r["networkChangeAllowed"])
                self.assertFalse(r["receipt"]["somaRuntimeWired"])

    def test_soma_demo_to_governor_is_advisory(self):
        r = run_demo()
        self.assertEqual(r["mode"], "OFFLINE_SYNTHETIC_READ_ONLY")
        self.assertEqual(r["corridor"]["state"], "REVIEW_CANDIDATE")
        self.assertFalse(r["corridor"]["physical_deployment_authorized"])
        self.assertFalse(r["corridor"]["rover_motion_authorized"])

    def test_receipts_deterministic_and_no_secrets(self):
        a = intake().receive(make_packet(), now_s=1001)["receipt"]
        b = intake().receive(make_packet(), now_s=1001)["receipt"]
        self.assertEqual(a, b)
        self.assertEqual(len(a["receipt_sha256"]), 64)
        self.assertNotIn(SECRET.hex(), json.dumps(a))
        self.assertNotIn("measurement", a)
        self.assertEqual(a["authentication"], "LAB_KEYRING_HMAC_ONLY")

    def test_replay_same_packet_refused(self):
        v = intake()
        p = make_packet()
        self.assertEqual(v.receive(p, now_s=1001)["status"], "ACCEPTED_ADVISORY_ONLY")
        self.assertEqual(v.receive(p, now_s=1001)["reason"], "REPLAY_OR_LEDGER_EXHAUSTED")

    def test_lower_sequence_refused(self):
        v = intake()
        self.assertEqual(v.receive(make_packet(sequence=5), now_s=1001)["status"], "ACCEPTED_ADVISORY_ONLY")
        self.assertEqual(v.receive(make_packet(sequence=4), now_s=1001)["reason"], "REPLAY_OR_LEDGER_EXHAUSTED")

    def test_reused_id_refused_even_with_new_sequence(self):
        v = intake()
        v.receive(make_packet(sequence=1), now_s=1001)
        self.assertEqual(v.receive(make_packet(sequence=2, observation_id="obs-1"), now_s=1001)["reason"],
                         "REPLAY_OR_LEDGER_EXHAUSTED")

    def test_ledger_saturation_fails_closed(self):
        v = intake(ReplayWindow(max_records=1))
        self.assertEqual(v.receive(make_packet(), now_s=1001)["status"], "ACCEPTED_ADVISORY_ONLY")
        self.assertEqual(v.receive(make_packet(sequence=2), now_s=1001)["reason"], "REPLAY_OR_LEDGER_EXHAUSTED")

    def test_no_mac_refused(self):
        p = make_packet()
        p["signature"]["mac_hex"] = "0" * 64
        self.assertEqual(intake().receive(p, now_s=1001)["reason"], "MAC_MISMATCH")

    def test_tampered_metric_rejected(self):
        p = make_packet()
        p["measurement"]["latency_ms"] = 40
        self.assertEqual(intake().receive(p, now_s=1001)["reason"], "MAC_MISMATCH")

    def test_key_substitution_refused(self):
        p = make_packet()
        p["signature"]["key_id"] = "alien-key"
        self.assertEqual(intake().receive(p, now_s=1001)["reason"], "UNPROVISIONED_PEER")

    def test_wrong_binding_refused(self):
        p = make_packet(node="relay")
        self.assertEqual(intake().receive(p, now_s=1001)["reason"], "UNPROVISIONED_PEER")

    def test_short_provisioning_key_refused(self):
        v = SomaIntake({"lab-rover-1": KeyBinding("lab", "rover", b"abc")})
        self.assertEqual(v.receive(make_packet(), now_s=1001)["reason"], "UNPROVISIONED_PEER")

    def test_invalid_clock_refused(self):
        self.assertEqual(intake().receive(make_packet(), now_s=float("nan"))["reason"], "INVALID_CLOCK")

    def test_negative_epoch_refused(self):
        self.assertEqual(intake().receive(make_packet(), now_s=-1)["reason"], "INVALID_CLOCK")
        p = make_packet(observed_at_s=-0.1)
        self.assertEqual(intake().receive(p, now_s=1001)["reason"], "STALE_OR_INVALID_TIME")

    def test_extreme_integer_fails_closed(self):
        p = make_packet()
        p["measurement"]["latency_ms"] = 10**1000
        self.assertEqual(intake().receive(p, now_s=1001)["reason"], "UNSAFE_MEASUREMENT")
        self.assertEqual(intake().receive(make_packet(), now_s=10**1000)["reason"], "INVALID_CLOCK")

    def test_stale_refused(self):
        self.assertEqual(intake().receive(make_packet(), now_s=1200)["reason"], "STALE_OR_INVALID_TIME")

    def test_future_refused(self):
        self.assertEqual(intake().receive(make_packet(), now_s=999)["reason"], "STALE_OR_INVALID_TIME")

    def test_nan_and_bool_numeric_refused(self):
        p = make_packet()
        p["measurement"]["latency_ms"] = float("nan")
        self.assertEqual(intake().receive(p, now_s=1001)["reason"], "UNSAFE_MEASUREMENT")
        p = make_packet()
        p["measurement"]["loss_pct"] = True
        self.assertEqual(intake().receive(p, now_s=1001)["reason"], "UNSAFE_MEASUREMENT")

    def test_unsafe_raw_camera_refused(self):
        p = make_packet("eyes.rover")
        p["measurement"]["jpeg_base64"] = "sensitive-camera-data"
        self.assertEqual(intake().receive(p, now_s=1001)["reason"], "UNSAFE_MEASUREMENT")

    def test_coordinates_refused(self):
        p = make_packet("sense.location")
        p["measurement"]["latitude"] = 45.0
        self.assertEqual(intake().receive(p, now_s=1001)["reason"], "UNSAFE_MEASUREMENT")

    def test_hidden_wifi_identifiers_refused(self):
        p = make_packet("sense.radio")
        p["measurement"]["ssid"] = "private-network"
        self.assertEqual(intake().receive(p, now_s=1001)["reason"], "UNSAFE_MEASUREMENT")

    def test_cross_node_network_claim_refused(self):
        p = make_packet()
        p["measurement"]["child_id"] = "relay"
        self.assertEqual(intake().receive(p, now_s=1001)["reason"], "UNSAFE_MEASUREMENT")

    def test_unknown_organ_refused(self):
        p = make_packet()
        p["organ"] = "hands.move"
        self.assertEqual(intake().receive(p, now_s=1001)["reason"], "UNKNOWN_ORGAN")

    def test_authority_escalation_refused(self):
        p = make_packet()
        p["authority"]["mayIssueHardwareCommands"] = True
        self.assertEqual(intake().receive(p, now_s=1001)["reason"], "AUTHORITY_ESCALATION")

    def test_tool_requests_refused(self):
        p = make_packet()
        p["toolRequests"] = ["sudo iwconfig"]
        self.assertEqual(intake().receive(p, now_s=1001)["reason"], "PACKET_SHAPE")

    def test_empty_or_bad_type_refused(self):
        self.assertEqual(intake().receive([], now_s=1001)["reason"], "INVALID_PACKET")
        p = make_packet()
        p["sequence"] = True
        self.assertEqual(intake().receive(p, now_s=1001)["reason"], "INVALID_SEQUENCE")

    def test_provenance_scope_and_version_refused(self):
        p = make_packet(site_id="another-site")
        self.assertEqual(intake().receive(p, now_s=1001)["reason"], "UNPROVISIONED_PEER")
        p = make_packet(contract="unknown")
        self.assertEqual(intake().receive(p, now_s=1001)["reason"], "CONTRACT_MISMATCH")

    def test_network_link_requires_admitted_message(self):
        result = admit_network_link(intake(), make_packet(), now_s=1001)
        self.assertEqual(result["status"], "OBSERVED_ADVISORY_ONLY")
        self.assertEqual(result["link"].parent, "base")
        self.assertEqual(result["link"].child, "rover")
        self.assertIsNone(result["link"].battery_pct)
        refused = admit_network_link(intake(), make_packet("sense.power"), now_s=1001)
        self.assertEqual(refused["status"], "HOLD")
        self.assertIsNone(refused["link"])

    def test_bad_packet_produces_no_link(self):
        p = make_packet()
        p["signature"]["mac_hex"] = "f" * 64
        result = admit_network_link(intake(), p, now_s=1001)
        self.assertEqual(result["status"], "HOLD")
        self.assertIsNone(result["link"])
        self.assertIsNone(result["receipt"])

    def test_receipt_does_not_grant_operators(self):
        out = intake().receive(make_packet(), now_s=1001)
        receipt = out["receipt"]
        for key in ("authorityGranted", "actionAuthorized", "mayInvokeTools", "mayIssueHardwareCommands"):
            self.assertIs(receipt[key], False)
        self.assertIs(receipt["safetyPlaneUnaffected"], True)

    def test_schema_contract_is_parseable_and_complete(self):
        schema_path = Path(__file__).resolve().parents[1] / "contracts" / "soma-observation.v0.1.schema.json"
        schema = json.loads(schema_path.read_text())
        self.assertEqual(len(schema["allOf"][1]["oneOf"]), len(ORGANS))
        self.assertEqual(schema["allOf"][0]["properties"]["contract"]["const"], CONTRACT)


if __name__ == "__main__":
    unittest.main()
