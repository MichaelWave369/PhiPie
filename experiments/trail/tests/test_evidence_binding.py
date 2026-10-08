"""ΦTrail local evidence hash binding acceptance. No physical hardware used."""
from __future__ import annotations

import copy
import io
import json
import os
from hashlib import sha256
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout

from trailcore.evidence_binding import (
    PATH_CONTRACT, SLOTS, manifest_template, verify_local_bundle,
)
from trailcore.evidence_cli import main
from trailcore.field_host import capture_host
from trailcore.field_witness import template
from trailcore.linux_radio import observe_radio
from trailcore.two_node_pilot import (
    create_lab_key, read_packet_file, receive_signed_radio,
    sign_complete_radio_report, write_private_json,
)
from trailcore.durable_replay import DurableReplayWindow


DEV = "phy#0\n    Interface wlan0\n        addr aa:bb:cc:dd:ee:ff\n"
LINK = ("Connected to aa:bb:cc:dd:ee:ff (on wlan0)\n"
        "    SSID: SecretForestNetwork\n    freq: 2412\n"
        "    signal: -58 dBm\n    tx bitrate: 72.2 MBit/s\n")
STATION_A = "Station aa:bb:cc:dd:ee:ff (on wlan0)\n    tx packets: 100\n    tx retries: 4\n"
STATION_B = "Station aa:bb:cc:dd:ee:ff (on wlan0)\n    tx packets: 120\n    tx retries: 6\n"


class FakeRunner:
    def __init__(self):
        self.reads = 0

    def run(self, argv, timeout_s=3):
        if argv == ("iw", "dev"):
            return 0, DEV
        if argv == ("iw", "dev", "wlan0", "link"):
            return 0, LINK
        if argv == ("iw", "dev", "wlan0", "station", "dump"):
            self.reads += 1
            return 0, STATION_A if self.reads == 1 else STATION_B
        return 1, ""


class EvidenceBindingTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.private = self.root / "artifacts"
        self.private.mkdir(mode=0o700)
        self.witness = template()
        self.manifest = manifest_template()
        self.witness["site_authorized"] = True
        self.witness["operator_present"] = True
        for idx, role in enumerate(("sender", "receiver")):
            host = capture_host(model_text="Raspberry Pi 5 Model B Rev 1",
                                clock=lambda: 1000.0 + idx, machine="aarch64",
                                kernel="6.12.22")
            radio = observe_radio("wlan0", runner=FakeRunner(),
                                  clock=lambda: 1001.0, sleeper=lambda _: None)
            write_private_json(self.private / self.manifest["files"][role+"_host"], host)
            write_private_json(self.private / self.manifest["files"][role+"_radio"], radio)
            node = next(x for x in self.witness["nodes"] if x["role"] == role)
            node.update({
                "platform": host["platform"], "evidence_origin": host["evidence_origin"],
                "host_snapshot_sha256": host["snapshot_sha256"],
                "radio_report_sha256": radio["evidence_sha256"],
                "boot_session_observed": True,
            })
            if role == "sender":
                sender_radio = radio
        key = self.root / "key.hex"
        ledger = self.root / "replay.db"
        create_lab_key(key)
        DurableReplayWindow.initialize(ledger)
        secret = bytes.fromhex(key.read_text().strip())
        packet = sign_complete_radio_report(
            sender_radio, site_id="lab", node_id="relay-a", peer_id="base-b",
            key_id="labkey", secret=secret, sequence=1, observation_id="obs-1",
        )
        self.assertIsNotNone(packet)
        packet_path = self.private / self.manifest["files"]["handoff_packet"]
        write_private_json(packet_path, packet)
        received = receive_signed_radio(
            packet, site_id="lab", node_id="relay-a", key_id="labkey",
            key_file=key, replay_db=ledger, now_s=1002,
        )
        self.assertEqual(received["status"], "ACCEPTED_ADVISORY_ONLY")
        write_private_json(self.private / self.manifest["files"]["handoff_receipt"], received)
        self.witness["handoff"].update({
            "manual_transfer_observed": True,
            "packet_sha256": sha256(packet_path.read_bytes()).hexdigest(),
            "receive_receipt_sha256": received["receipt"]["receipt_sha256"],
            "accepted_advisory_only": True,
            "replay_refused_after_restart": True,
            "tamper_refused": True,
            "clock_method": "NTP_OBSERVED", "clock_skew_ms": 5.0,
        })
        path_data = {
            "schema": PATH_CONTRACT, "kind": "ICMP", "packet_loss_pct": 0.0,
            "rtt_avg_ms": 12.3, "throughput_mbps": None,
            "independent_test_run": True,
            "evidence_origin": "OPERATOR_RECORDED_INDEPENDENT",
        }
        path = self.private / self.manifest["files"]["path_test"]
        write_private_json(path, path_data)
        self.witness["path_test"].update({
            "independent_test_run": True, "kind": "ICMP",
            "evidence_sha256": sha256(path.read_bytes()).hexdigest(),
            "packet_loss_pct": 0.0, "rtt_avg_ms": 12.3,
            "throughput_mbps": None,
        })
        self.witness["safety"].update({
            "no_network_writes_observed": True,
            "no_rover_motion_observed": True,
            "no_relay_deployment_observed": True,
        })

    def run_verify(self):
        return verify_local_bundle(self.witness, self.manifest, self.private)

    def rewrite(self, slot, item):
        path = self.private / self.manifest["files"][slot]
        path.unlink()
        write_private_json(path, item)
        return path

    def test_complete_private_consistency_but_no_hardware_qualification(self):
        result = self.run_verify()
        self.assertEqual(result["status"], "LOCAL_EVIDENCE_MATCH")
        self.assertTrue(all(v == "MATCH" for v in result["checks"].values()))
        self.assertFalse(result["physical_hardware_qualified"])
        self.assertFalse(result["mesh_transport_verified"])
        self.assertFalse(result["hmac_cryptographically_verified"])
        self.assertFalse(result["action_authorized"])

    def test_checksum_is_deterministic(self):
        self.assertEqual(self.run_verify(), self.run_verify())

    def test_no_secret_path_or_sensitive_data_in_output(self):
        out = json.dumps(self.run_verify())
        for forbidden in ("SecretForestNetwork", "aa:bb:cc:dd:ee:ff",
                          str(self.private), "labkey", "obs-1"):
            self.assertNotIn(forbidden, out)

    def test_missing_radio_file_refused(self):
        (self.private / self.manifest["files"]["receiver_radio"]).unlink()
        result = self.run_verify()
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("RECEIVER_RADIO_UNREADABLE_OR_UNSAFE", result["reasons"])

    def test_host_tamper_detected(self):
        name = self.manifest["files"]["sender_host"]
        host = read_packet_file(self.private / name)
        host["kernel_major_minor"] = "7.99"
        self.rewrite("sender_host", host)
        self.assertIn("SENDER_HOST_EVIDENCE_MISMATCH", self.run_verify()["reasons"])

    def test_radio_tamper_detected(self):
        name = self.manifest["files"]["sender_radio"]
        radio = read_packet_file(self.private / name)
        radio["metrics"]["rssi_dbm"] = -12
        self.rewrite("sender_radio", radio)
        self.assertIn("SENDER_RADIO_EVIDENCE_MISMATCH", self.run_verify()["reasons"])

    def test_signed_packet_bytes_must_match(self):
        name = self.manifest["files"]["handoff_packet"]
        packet = read_packet_file(self.private / name)
        packet["observation_id"] = "modified"
        self.rewrite("handoff_packet", packet)
        self.assertIn("HANDOFF_PACKET_MISMATCH", self.run_verify()["reasons"])

    def test_receipt_cross_reference_detects_fabrication(self):
        name = self.manifest["files"]["handoff_receipt"]
        receipt = read_packet_file(self.private / name)
        receipt["receipt"]["observation_id"] = "modified"
        self.rewrite("handoff_receipt", receipt)
        self.assertIn("HANDOFF_RECEIPT_MISMATCH", self.run_verify()["reasons"])

    def test_path_metrics_disagreeing_with_witness_refused(self):
        name = self.manifest["files"]["path_test"]
        path = read_packet_file(self.private / name)
        path["rtt_avg_ms"] = 1000
        self.rewrite("path_test", path)
        self.assertIn("PATH_EVIDENCE_MISMATCH", self.run_verify()["reasons"])

    def test_template_witness_still_holds(self):
        self.assertEqual(verify_local_bundle(template(), self.manifest, self.private)["status"], "HOLD")

    def test_simulated_witness_refused(self):
        self.witness["mode"] = "LAB_SIMULATION"
        self.assertIn("FIELD_WITNESS_INCOMPLETE", self.run_verify()["reasons"])

    def test_missing_site_permission_holds(self):
        self.witness["site_authorized"] = False
        self.assertEqual(self.run_verify()["status"], "HOLD")

    def test_manifest_wrong_test_id(self):
        self.manifest["test_id"] = "other"
        self.assertIn("INVALID_PRIVATE_MANIFEST", self.run_verify()["reasons"])

    def test_manifest_unknown_slot(self):
        self.manifest["files"]["credential"] = "key.hex"
        self.assertIn("INVALID_PRIVATE_MANIFEST", self.run_verify()["reasons"])

    def test_manifest_rejects_duplicate_filenames(self):
        self.manifest["files"]["sender_radio"] = self.manifest["files"]["sender_host"]
        self.assertIn("INVALID_PRIVATE_MANIFEST", self.run_verify()["reasons"])

    def test_manifest_rejects_directory_traversal(self):
        for malicious in ("../../secret.json", "/etc/passwd", "radio.json/..",
                          "name;reboot.json", "radio.txt", "A"*80+".json"):
            with self.subTest(name=malicious):
                altered = copy.deepcopy(self.manifest)
                altered["files"]["sender_host"] = malicious
                result = verify_local_bundle(self.witness, altered, self.private)
                self.assertIn("INVALID_PRIVATE_MANIFEST", result["reasons"])

    def test_symlink_evidence_refused(self):
        target = self.private / self.manifest["files"]["sender_host"]
        other = self.private / "other.json"
        target.rename(other)
        try:
            target.symlink_to(other)
        except OSError:
            self.skipTest("symlinks unavailable")
        self.assertEqual(self.run_verify()["checks"]["sender_host"], "HOLD")

    def test_private_dir_symlink_refused(self):
        link = self.root / "artifacts-link"
        try:
            link.symlink_to(self.private)
        except OSError:
            self.skipTest("symlinks unavailable")
        result = verify_local_bundle(self.witness, self.manifest, link)
        self.assertIn("PRIVATE_EVIDENCE_DIRECTORY_UNSAFE", result["reasons"])

    def test_file_world_readable_refused(self):
        if os.name != "posix":
            self.skipTest("POSIX only")
        (self.private / self.manifest["files"]["sender_host"]).chmod(0o644)
        self.assertIn("SENDER_HOST_UNREADABLE_OR_UNSAFE", self.run_verify()["reasons"])

    def test_dir_world_readable_refused(self):
        if os.name != "posix":
            self.skipTest("POSIX only")
        self.private.chmod(0o755)
        self.assertIn("PRIVATE_EVIDENCE_DIRECTORY_UNSAFE", self.run_verify()["reasons"])

    def test_evidence_file_oversize_refused(self):
        # Bypass the deliberately size-limited normal writer to create hostile input.
        p = self.private / self.manifest["files"]["receiver_host"]
        p.unlink()
        p.write_bytes(b"X" * 17000)
        if os.name == "posix":
            p.chmod(0o600)
        self.assertIn("RECEIVER_HOST_UNREADABLE_OR_UNSAFE", self.run_verify()["reasons"])

    def test_json_duplicate_keys_refused(self):
        p = self.private / self.manifest["files"]["sender_host"]
        p.unlink()
        p.write_text('{"schema":1,"schema":2}')
        if os.name == "posix": p.chmod(0o600)
        self.assertIn("SENDER_HOST_UNREADABLE_OR_UNSAFE", self.run_verify()["reasons"])

    def test_bad_json_constant_refused(self):
        p = self.private / self.manifest["files"]["sender_host"]
        p.unlink()
        p.write_text('{"captured_at_s":NaN}')
        if os.name == "posix": p.chmod(0o600)
        self.assertIn("SENDER_HOST_UNREADABLE_OR_UNSAFE", self.run_verify()["reasons"])

    def test_receipt_wrong_authority_refused(self):
        p = self.private / self.manifest["files"]["handoff_receipt"]
        record = read_packet_file(p)
        record["receipt"]["mayIssueHardwareCommands"] = True
        self.rewrite("handoff_receipt", record)
        self.assertIn("HANDOFF_RECEIPT_MISMATCH", self.run_verify()["reasons"])

    def test_host_model_claims_must_match(self):
        self.witness["nodes"][0]["platform"] = "CM5_REPORTED"
        self.assertIn("SENDER_HOST_EVIDENCE_MISMATCH", self.run_verify()["reasons"])

    def test_partial_radio_can_be_bound_without_claiming_radio_qualification(self):
        p = self.private / self.manifest["files"]["sender_radio"]
        radio = read_packet_file(p)
        radio["status"] = "PARTIAL"
        radio["metrics"]["retry_pct"] = None
        radio["metrics"]["sample_count"] = None
        from trailcore.soma_observation import canonical_json
        radio.pop("evidence_sha256")
        radio["evidence_sha256"] = sha256(canonical_json(radio)).hexdigest()
        self.rewrite("sender_radio", radio)
        self.witness["nodes"][0]["radio_report_sha256"] = radio["evidence_sha256"]
        result = self.run_verify()
        self.assertEqual(result["status"], "LOCAL_EVIDENCE_MATCH")
        self.assertFalse(result["physical_hardware_qualified"])

    def test_cli_manifest_and_review(self):
        mf = self.root / "manifest.json"
        witness = self.root / "witness.json"
        output = self.root / "result.json"
        write_private_json(witness, self.witness)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(["manifest", "--output", str(mf)]), 0)
            self.assertEqual(main([
                "inspect", "--witness", str(witness), "--manifest", str(mf),
                "--evidence-dir", str(self.private), "--output", str(output)
            ]), 0)
        obj = read_packet_file(output)
        self.assertEqual(obj["status"], "LOCAL_EVIDENCE_MATCH")
        self.assertFalse(obj["field_identity_attested"])

    def test_cli_no_clobber(self):
        mf = self.root / "manifest.json"
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(["manifest", "--output", str(mf)]), 0)
            self.assertEqual(main(["manifest", "--output", str(mf)]), 2)

    def test_missing_handoff_receipt_self_hash_holds(self):
        name = self.manifest["files"]["handoff_receipt"]
        receipt = read_packet_file(self.private / name)
        del receipt["receipt"]["receipt_sha256"]
        self.rewrite("handoff_receipt", receipt)
        self.assertIn("HANDOFF_RECEIPT_MISMATCH", self.run_verify()["reasons"])

    def test_invalid_input_has_no_hardware_authority(self):
        for bad in (None, [], {}, "wrong"):
            with self.subTest(bad=bad):
                report = verify_local_bundle(bad, self.manifest, self.private)
                self.assertEqual(report["status"], "HOLD")
                self.assertFalse(report["physical_hardware_qualified"])
                self.assertFalse(report["network_change_authorized"])


if __name__ == "__main__":
    unittest.main()
