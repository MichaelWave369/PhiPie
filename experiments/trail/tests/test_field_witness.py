"""Offline verification of the PhiPie two-node field-witness protocol."""
from __future__ import annotations

import copy
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout

from trailcore.field_host import capture_host
from trailcore.field_witness import assess_witness, template
from trailcore.field_cli import main
from trailcore.two_node_pilot import write_private_json, read_packet_file


DIGEST = "b" * 64


def complete():
    w = template()
    w["site_authorized"] = True
    w["operator_present"] = True
    for node in w["nodes"]:
        node["platform"] = "RPI5_REPORTED"
        node["evidence_origin"] = "LOCAL_LINUX"
        node["host_snapshot_sha256"] = DIGEST
        node["radio_report_sha256"] = DIGEST
        node["boot_session_observed"] = True
    w["handoff"] = {
        "manual_transfer_observed": True, "packet_sha256": DIGEST,
        "receive_receipt_sha256": DIGEST, "accepted_advisory_only": True,
        "replay_refused_after_restart": True, "tamper_refused": True,
        "clock_method": "NTP_OBSERVED", "clock_skew_ms": 5.0,
    }
    w["path_test"] = {
        "independent_test_run": True, "kind": "ICMP",
        "evidence_sha256": DIGEST, "packet_loss_pct": 0.0,
        "rtt_avg_ms": 12.2, "throughput_mbps": None,
    }
    w["safety"] = {
        "no_network_writes_observed": True,
        "no_rover_motion_observed": True,
        "no_relay_deployment_observed": True,
    }
    return w


class FieldWitnessTests(unittest.TestCase):
    def test_default_template_holds(self):
        w = template()
        self.assertEqual(assess_witness(w)["status"], "HOLD")
        self.assertIsNone(w["handoff"]["packet_sha256"])

    def test_fully_attested_report_still_unqualified(self):
        x = assess_witness(complete())
        self.assertEqual(x["status"], "OPERATOR_REVIEW_CANDIDATE")
        self.assertEqual(x["reasons"], [])
        for k in ("hardware_physically_qualified", "mesh_transport_verified",
                  "emergency_coverage_verified", "action_authorized",
                  "network_change_authorized", "rover_motion_authorized",
                  "soma_runtime_wired"):
            self.assertIs(x[k], False, k)
        self.assertTrue(x["operator_claims_only"])

    def test_result_is_deterministic(self):
        self.assertEqual(assess_witness(complete()), assess_witness(complete()))

    def test_lab_simulation_cannot_promote(self):
        w = complete()
        w["mode"] = "LAB_SIMULATION"
        self.assertIn("SIMULATION_CANNOT_QUALIFY_FIELD", assess_witness(w)["reasons"])

    def test_fake_origin_blocks_field(self):
        w = complete()
        w["nodes"][1]["evidence_origin"] = "SYNTHETIC"
        self.assertIn("PHYSICAL_PI_OBSERVATION_MISSING", assess_witness(w)["reasons"])

    def test_unknown_platform_holds(self):
        w = complete()
        w["nodes"][1]["platform"] = "UNKNOWN"
        self.assertEqual(assess_witness(w)["status"], "HOLD")

    def test_site_permission_missing_holds(self):
        w = complete()
        w["site_authorized"] = False
        self.assertEqual(assess_witness(w)["status"], "HOLD")

    def test_operator_absent_holds(self):
        w = complete()
        w["operator_present"] = False
        self.assertEqual(assess_witness(w)["status"], "HOLD")

    def test_duplicate_node_roles_holds(self):
        w = complete()
        w["nodes"][1]["role"] = "sender"
        self.assertIn("DUPLICATE_OR_INVALID_ROLE", assess_witness(w)["reasons"])

    def test_duplicate_node_identity_holds(self):
        w = complete()
        w["nodes"][1]["node_id"] = "relay-a"
        self.assertIn("DUPLICATE_OR_INVALID_NODE", assess_witness(w)["reasons"])

    def test_required_hash_missing_holds(self):
        w = complete()
        w["handoff"]["receive_receipt_sha256"] = None
        self.assertEqual(assess_witness(w)["status"], "HOLD")

    def test_missing_replay_refusal_holds(self):
        w = complete()
        w["handoff"]["replay_refused_after_restart"] = False
        self.assertEqual(assess_witness(w)["status"], "HOLD")

    def test_missing_tamper_control_holds(self):
        w = complete()
        w["handoff"]["tamper_refused"] = False
        self.assertEqual(assess_witness(w)["status"], "HOLD")

    def test_unknown_clock_holds(self):
        w = complete()
        w["handoff"]["clock_method"] = "UNKNOWN"
        self.assertEqual(assess_witness(w)["status"], "HOLD")

    def test_clock_skew_over_bound_holds(self):
        w = complete()
        w["handoff"]["clock_skew_ms"] = 90_001
        self.assertEqual(assess_witness(w)["status"], "HOLD")

    def test_icmp_throughput_is_not_fabricated(self):
        w = complete()
        w["path_test"]["throughput_mbps"] = 30
        self.assertIn("ICMP_THROUGHPUT_MUST_BE_UNKNOWN", assess_witness(w)["reasons"])

    def test_tcp_test_needs_throughput(self):
        w = complete()
        w["path_test"]["kind"] = "TCP_BENCHMARK"
        self.assertIn("THROUGHPUT_EVIDENCE_MISSING", assess_witness(w)["reasons"])
        w["path_test"]["throughput_mbps"] = 18.0
        self.assertEqual(assess_witness(w)["status"], "OPERATOR_REVIEW_CANDIDATE")

    def test_unperformed_path_test_holds(self):
        w = complete()
        w["path_test"]["independent_test_run"] = False
        self.assertEqual(assess_witness(w)["status"], "HOLD")

    def test_safety_unconfirmed_holds(self):
        w = complete()
        w["safety"]["no_network_writes_observed"] = False
        self.assertEqual(assess_witness(w)["status"], "HOLD")

    def test_unknown_field_refused_no_disclosure(self):
        w = complete()
        w["nodes"][0]["ssid"] = "PrivateHome"
        x = assess_witness(w)
        self.assertIn("INVALID_NODE_SHAPE", x["reasons"])
        self.assertNotIn("PrivateHome", json.dumps(x))
        w = complete()
        w["mac"] = "aa:bb:cc:dd:ee:ff"
        self.assertIn("INVALID_TOP_LEVEL_SHAPE", assess_witness(w)["reasons"])

    def test_malformed_top_level_fails_closed(self):
        for value in ([], None, "abc", 4, {}, {"schema": "other"}):
            with self.subTest(value=value):
                self.assertEqual(assess_witness(value)["status"], "HOLD")

    def test_wrong_node_collection_fails_closed(self):
        w = complete()
        w["nodes"] = []
        self.assertIn("TWO_NODE_EVIDENCE_REQUIRED", assess_witness(w)["reasons"])

    def test_nonfinite_metrics_fail_closed(self):
        w = complete()
        w["path_test"]["rtt_avg_ms"] = float("nan")
        self.assertEqual(assess_witness(w)["status"], "HOLD")
        self.assertIsNone(assess_witness(w)["witness_sha256"])

    def test_adversarial_unhashable_values_refuse(self):
        w = complete()
        for field, value in (("mode", []), ("mode", {}), ("mode", None)):
            clone = copy.deepcopy(w)
            clone[field] = value
            self.assertEqual(assess_witness(clone)["status"], "HOLD")
        clone = complete()
        clone["nodes"][0]["role"] = ["sender"]
        self.assertEqual(assess_witness(clone)["status"], "HOLD")
        clone = complete()
        clone["path_test"]["kind"] = []
        self.assertEqual(assess_witness(clone)["status"], "HOLD")

    def test_host_snapshot_only_coarse_information(self):
        host = capture_host(model_text="Raspberry Pi 5 Model B Rev 1.0",
                            clock=lambda: 1000.0, machine="aarch64",
                            kernel="6.12.34-xxx")
        self.assertEqual(host["platform"], "RPI5_REPORTED")
        self.assertEqual(host["architecture"], "aarch64")
        self.assertEqual(host["kernel_major_minor"], "6.12")
        self.assertFalse(host["hardware_attested"])
        self.assertFalse(host["clock_trusted"])
        self.assertEqual(len(host["snapshot_sha256"]), 64)
        self.assertNotIn("Rev", json.dumps(host))

    def test_unknown_platform_snapshot_is_not_pi(self):
        host = capture_host(model_text="", clock=lambda: 1, machine="mystery",
                            kernel="strange")
        self.assertEqual(host["platform"], "UNKNOWN")
        self.assertEqual(host["architecture"], "OTHER")
        self.assertEqual(host["kernel_major_minor"], "UNKNOWN")

    def test_invalid_host_clock_is_unknown(self):
        host = capture_host(model_text="Raspberry Pi 5 Model B", clock=lambda: float("nan"),
                            machine="aarch64", kernel="6.12")
        self.assertIsNone(host["captured_at_s"])

    def test_output_is_private_and_never_clobbered(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.assertEqual(main(["template", "--output", str(path)]), 0)
            self.assertEqual(read_packet_file(path), template())
            if os.name == "posix":
                self.assertEqual(path.stat().st_mode & 0o077, 0)
            with redirect_stdout(buf):
                self.assertEqual(main(["template", "--output", str(path)]), 2)

    def test_cli_assessment_produces_private_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp, out = Path(tmp) / "input.json", Path(tmp) / "out.json"
            write_private_json(inp, complete())
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(["assess", "--input", str(inp),
                                       "--output", str(out)]), 0)
            report = read_packet_file(out)
            self.assertEqual(report["status"], "OPERATOR_REVIEW_CANDIDATE")
            self.assertFalse(report["hardware_physically_qualified"])

    def test_cli_invalid_input_reports_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp, out = Path(tmp) / "input.json", Path(tmp) / "out.json"
            inp.write_text('{"x":1,"x":2}')
            if os.name == "posix":
                inp.chmod(0o600)
            buf = io.StringIO()
            with redirect_stdout(buf):
                status = main(["assess", "--input", str(inp),
                               "--output", str(out)])
            self.assertEqual(status, 2)
            self.assertEqual(json.loads(buf.getvalue())["status"], "HOLD")
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
