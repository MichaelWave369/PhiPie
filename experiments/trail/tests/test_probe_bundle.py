"""PhiPie PR18: opt-in ping evidence and eight-file binding, entirely fake IO."""
from __future__ import annotations
import copy
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from trailcore.field_witness import template
from trailcore.field_host import capture_host
from trailcore.linux_radio import observe_radio
from trailcore.path_probe import collect_icmp_pair
from trailcore.path_probe_cli import main as path_main
from trailcore.probe_bundle import (
    probe_manifest_template, verify_probe_bundle, _valid_probe,
)
from trailcore.probe_bundle_cli import main as bundle_main
from trailcore.two_node_pilot import (
    create_lab_key, sign_complete_radio_report, receive_signed_radio,
    write_private_json, read_packet_file,
)
from trailcore.durable_replay import DurableReplayWindow


DEV = "phy#0\n    Interface wlan0\n        addr aa:bb:cc:dd:ee:ff\n"
LINK = ("Connected to aa:bb:cc:dd:ee:ff (on wlan0)\n"
        "    SSID: SecretForestNetwork\n    freq: 2412\n"
        "    signal: -58 dBm\n    tx bitrate: 72.2 MBit/s\n")
STA1 = "Station aa:bb:cc:dd:ee:ff (on wlan0)\n    tx packets: 100\n    tx retries: 4\n"
STA2 = "Station aa:bb:cc:dd:ee:ff (on wlan0)\n    tx packets: 120\n    tx retries: 6\n"
PING = ("3 packets transmitted, 3 received, 0% packet loss, time 2000ms\n"
        "rtt min/avg/max/mdev = 7.200/8.433/10.100/1.240 ms\n")


class FakeRunner:
    def __init__(self):
        self.calls = []
        self.counter = 0

    def run(self, argv, timeout_s=3):
        self.calls.append(argv)
        if argv == ("iw", "dev"):
            return 0, DEV
        if argv == ("iw", "dev", "wlan0", "link"):
            return 0, LINK
        if argv == ("iw", "dev", "wlan0", "station", "dump"):
            self.counter += 1
            return 0, STA1 if self.counter == 1 else STA2
        if argv == ("ping", "-n", "-I", "wlan0", "-c", "3", "-W", "1", "192.168.1.1"):
            return 0, PING
        return 1, ""


class ProbeBundleTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.private = self.root / "private"
        self.private.mkdir(mode=0o700)
        self.manifest = probe_manifest_template()
        self.witness = template()
        self.witness["site_authorized"] = True
        self.witness["operator_present"] = True
        self.runner = FakeRunner()
        pair = collect_icmp_pair("192.168.1.1", "wlan0",
                                 approved=True, runner=self.runner)
        self.assertEqual(pair["status"], "LOCAL_PROBE_OBSERVED")
        self.pair = pair
        for index, role in enumerate(("sender", "receiver")):
            host = capture_host(model_text="Raspberry Pi 5 Model B Rev 1",
                                clock=lambda: 1001.0, machine="aarch64",
                                kernel="6.12.34")
            report = observe_radio("wlan0", runner=FakeRunner(),
                                   sleeper=lambda _: None, clock=lambda: 1001.0)
            self.assertEqual(report["status"], "COMPLETE")
            write_private_json(self.private / self.manifest["files"][role+"_host"], host)
            write_private_json(self.private / self.manifest["files"][role+"_radio"], report)
            node = next(x for x in self.witness["nodes"] if x["role"] == role)
            node.update({
                "platform": host["platform"], "evidence_origin": host["evidence_origin"],
                "host_snapshot_sha256": host["snapshot_sha256"],
                "radio_report_sha256": report["evidence_sha256"],
                "boot_session_observed": True,
            })
            if role == "sender":
                sender = report
        key = self.root / "key.hex"
        replay = self.root / "replay.db"
        create_lab_key(key)
        DurableReplayWindow.initialize(replay)
        packet = sign_complete_radio_report(
            sender, site_id="lab", node_id="relay-a", peer_id="base-b",
            key_id="lab-key", secret=bytes.fromhex(key.read_text().strip()),
            sequence=1, observation_id="obs-1",
        )
        self.assertIsNotNone(packet)
        handoff = self.private / self.manifest["files"]["handoff_packet"]
        write_private_json(handoff, packet)
        receipt = receive_signed_radio(
            packet, site_id="lab", node_id="relay-a", key_id="lab-key",
            key_file=key, replay_db=replay, now_s=1002,
        )
        self.assertEqual(receipt["status"], "ACCEPTED_ADVISORY_ONLY")
        write_private_json(self.private / self.manifest["files"]["handoff_receipt"], receipt)
        self.witness["handoff"].update({
            "manual_transfer_observed": True,
            "packet_sha256": sha256(handoff.read_bytes()).hexdigest(),
            "receive_receipt_sha256": receipt["receipt"]["receipt_sha256"],
            "accepted_advisory_only": True, "replay_refused_after_restart": True,
            "tamper_refused": True, "clock_method": "NTP_OBSERVED",
            "clock_skew_ms": 4.0,
        })
        path_file = self.private / self.manifest["files"]["path_test"]
        write_private_json(path_file, pair["path_record"])
        write_private_json(self.private / self.manifest["files"]["icmp_probe"], pair["probe"])
        self.witness["path_test"].update({
            "independent_test_run": True, "kind": "ICMP",
            "evidence_sha256": sha256(path_file.read_bytes()).hexdigest(),
            "packet_loss_pct": 0.0, "rtt_avg_ms": 8.433, "throughput_mbps": None,
        })
        self.witness["safety"].update({
            "no_network_writes_observed": True, "no_rover_motion_observed": True,
            "no_relay_deployment_observed": True,
        })

    def check(self):
        return verify_probe_bundle(self.witness, self.manifest, self.private)

    def rewrite(self, slot, record):
        p = self.private / self.manifest["files"][slot]
        p.unlink()
        write_private_json(p, record)

    def test_complete_local_probe_pair_still_non_qualifying(self):
        outcome = self.check()
        self.assertEqual(outcome["status"], "LOCAL_PROBE_EVIDENCE_MATCH")
        self.assertEqual(set(outcome["checks"]), set(self.manifest["files"]))
        self.assertTrue(all(v == "MATCH" for v in outcome["checks"].values()))
        for field in (
            "host_attested", "sender_authenticated", "physical_hardware_qualified",
            "routed_network_verified", "mesh_transport_verified",
            "measured_throughput", "emergency_coverage_verified",
            "network_change_authorized", "rover_motion_authorized",
            "soma_runtime_wired",
        ):
            self.assertIs(outcome[field], False, field)

    def test_output_hides_sensitive_network_identifiers(self):
        output = json.dumps(self.check())
        for forbidden in ("192.168.1.1", "SecretForestNetwork", "aa:bb:cc",
                          str(self.private), "lab-key"):
            self.assertNotIn(forbidden, output)

    def test_approved_probe_exactly_one_bounded_ping(self):
        cmds = [x for x in self.runner.calls if x[0] == "ping"]
        self.assertEqual(len(cmds), 1)
        self.assertEqual(cmds[0][4:8], ("-c", "3", "-W", "1"))

    def test_no_approval_sends_zero_traffic(self):
        runner = FakeRunner()
        obj = collect_icmp_pair("192.168.1.1", "wlan0", approved=False, runner=runner)
        self.assertEqual(obj["status"], "HOLD")
        self.assertEqual(runner.calls, [])

    def test_public_target_sends_zero_traffic(self):
        runner = FakeRunner()
        result = collect_icmp_pair("8.8.8.8", "wlan0", approved=True, runner=runner)
        self.assertEqual(result["status"], "HOLD")
        self.assertEqual(runner.calls, [])

    def test_raw_probe_digest_tampering_refused(self):
        altered = copy.deepcopy(self.pair["probe"])
        altered["metrics"]["probe_rtt_avg_ms"] = 20
        self.rewrite("icmp_probe", altered)
        self.assertIn("PROBE_TO_PATH_MISMATCH", self.check()["reasons"])

    def test_consistent_rewrite_not_authorized_as_probe(self):
        altered = copy.deepcopy(self.pair["probe"])
        altered["provenance"]["traffic_generated"] = False
        self.rewrite("icmp_probe", altered)
        self.assertEqual(self.check()["status"], "HOLD")

    def test_fabricated_throughput_refused(self):
        obj = copy.deepcopy(self.pair["path_record"])
        obj["throughput_mbps"] = 22
        self.rewrite("path_test", obj)
        self.assertEqual(self.check()["status"], "HOLD")

    def test_missing_probe_refused(self):
        (self.private / self.manifest["files"]["icmp_probe"]).unlink()
        self.assertIn("PROBE_UNREADABLE_OR_UNSAFE", self.check()["reasons"])

    def test_missing_legacy_evidence_refused(self):
        (self.private / self.manifest["files"]["receiver_host"]).unlink()
        self.assertIn("SEVEN_FILE_BASELINE_HOLD", self.check()["reasons"])

    def test_fake_origin_fails_inherited_witness(self):
        self.witness["mode"] = "LAB_SIMULATION"
        self.assertEqual(self.check()["status"], "HOLD")

    def test_duplicate_manifest_filenames_refused(self):
        self.manifest["files"]["icmp_probe"] = self.manifest["files"]["path_test"]
        self.assertIn("INVALID_PROBE_MANIFEST", self.check()["reasons"])

    def test_manifest_path_escape_refused(self):
        self.manifest["files"]["icmp_probe"] = "../../secret.json"
        self.assertIn("INVALID_PROBE_MANIFEST", self.check()["reasons"])

    def test_extra_unknown_manifest_slot_refused(self):
        self.manifest["files"]["credential_file"] = "key.hex"
        self.assertIn("INVALID_PROBE_MANIFEST", self.check()["reasons"])

    def test_symlink_probe_refused(self):
        p = self.private / self.manifest["files"]["icmp_probe"]
        q = self.private / "original.json"
        p.rename(q)
        try:
            p.symlink_to(q)
        except OSError:
            self.skipTest("symlinks unsupported")
        self.assertEqual(self.check()["status"], "HOLD")

    def test_unsafe_directory_refused(self):
        if os.name != "posix":
            self.skipTest("POSIX only")
        self.private.chmod(0o755)
        self.assertEqual(self.check()["status"], "HOLD")

    def test_probe_world_readable_refused(self):
        if os.name != "posix":
            self.skipTest("POSIX only")
        (self.private / self.manifest["files"]["icmp_probe"]).chmod(0o644)
        self.assertEqual(self.check()["status"], "HOLD")

    def test_probe_to_path_mismatch_refused_even_with_local_hashes(self):
        changed = copy.deepcopy(self.pair["path_record"])
        changed["rtt_avg_ms"] = 9.0
        self.rewrite("path_test", changed)
        self.witness["path_test"]["rtt_avg_ms"] = 9.0
        p = self.private / self.manifest["files"]["path_test"]
        self.witness["path_test"]["evidence_sha256"] = sha256(p.read_bytes()).hexdigest()
        result = self.check()
        self.assertIn("PROBE_TO_PATH_MISMATCH", result["reasons"])

    def test_invalid_metrics_refused(self):
        for x in (None, "8.4", True, float("nan")):
            probe = copy.deepcopy(self.pair["probe"])
            probe["metrics"]["probe_rtt_avg_ms"] = x
            self.assertFalse(_valid_probe(probe, self.pair["path_record"]))

    def test_synthetic_positive_output_is_not_field_proof(self):
        self.assertIs(self.check()["physical_hardware_qualified"], False)

    def test_collector_cli_without_approval_does_no_io(self):
        out = io.StringIO()
        probe, path = self.root / "new-probe.json", self.root / "new-path.json"
        with redirect_stdout(out):
            status = path_main([
                "--interface", "wlan0", "--target", "192.168.1.1",
                "--probe-out", str(probe), "--path-out", str(path),
            ])
        self.assertEqual(status, 2)
        self.assertFalse(probe.exists())
        self.assertFalse(path.exists())
        self.assertEqual(json.loads(out.getvalue())["reason"],
                         "OPERATOR_PROBE_APPROVAL_REQUIRED")

    def test_collector_cli_emits_private_files_with_mocked_probe(self):
        probe, path = self.root / "new-probe.json", self.root / "new-path.json"
        with patch("trailcore.path_probe_cli.collect_icmp_pair", return_value=self.pair):
            with redirect_stdout(io.StringIO()) as out:
                status = path_main([
                    "--interface", "wlan0", "--target", "192.168.1.1",
                    "--approve-probe", "--probe-out", str(probe),
                    "--path-out", str(path),
                ])
        self.assertEqual(status, 0)
        self.assertEqual(read_packet_file(probe), self.pair["probe"])
        self.assertEqual(read_packet_file(path), self.pair["path_record"])
        self.assertNotIn("192.168.1.1", out.getvalue())

    def test_eight_file_cli_accepts_consistent_fixture(self):
        wit, manifest, output = (self.root / name for name in (
            "trial.json", "manifest-v2.json", "assessment.json",
        ))
        write_private_json(wit, self.witness)
        write_private_json(manifest, self.manifest)
        with redirect_stdout(io.StringIO()):
            status = bundle_main([
                "inspect", "--witness", str(wit), "--manifest", str(manifest),
                "--evidence-dir", str(self.private), "--output", str(output),
            ])
        self.assertEqual(status, 0)
        self.assertEqual(read_packet_file(output)["status"], "LOCAL_PROBE_EVIDENCE_MATCH")

    def test_template_creates_eight_slots(self):
        manifest = probe_manifest_template()
        self.assertEqual(len(manifest["files"]), 8)
        self.assertEqual(len(set(manifest["files"].values())), 8)


if __name__ == "__main__":
    unittest.main()
