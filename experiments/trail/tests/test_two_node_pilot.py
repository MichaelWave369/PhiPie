"""ΦTrail two-node evidence pilot: no actual radios, networking or field secrets."""
from __future__ import annotations

import copy
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from contextlib import redirect_stdout

from trailcore.durable_replay import DurableReplayWindow
from trailcore.soma_observation import KeyBinding, SomaIntake
from trailcore.two_node_pilot import (
    create_lab_key, read_lab_key, collect_signed_radio, read_packet_file,
    receive_signed_radio, sign_complete_radio_report, write_private_json,
)
from trailcore.two_node_cli import main

SECRET = bytes(range(32))
DEV = """phy#0
    Interface wlan0
        addr aa:bb:cc:dd:ee:ff
        type managed
"""
LINK = """Connected to aa:bb:cc:dd:ee:ff (on wlan0)
    SSID: HiddenCampNetwork
    freq: 2412
    signal: -63 dBm
    tx bitrate: 72.2 MBit/s
"""
STATION_A = """Station aa:bb:cc:dd:ee:ff (on wlan0)
    tx packets: 100
    tx retries: 4
"""
STATION_B = """Station aa:bb:cc:dd:ee:ff (on wlan0)
    tx packets: 112
    tx retries: 7
"""


class FakeRunner:
    def __init__(self, *, missing_retries=False):
        self.calls = []
        self.reads = 0
        self.missing_retries = missing_retries

    def run(self, argv, timeout_s=3.0):
        self.calls.append(tuple(argv))
        if argv == ("iw", "dev"):
            return 0, DEV
        if argv == ("iw", "dev", "wlan0", "link"):
            return 0, LINK
        if argv == ("iw", "dev", "wlan0", "station", "dump"):
            self.reads += 1
            if self.missing_retries:
                return 0, ""
            return 0, STATION_A if self.reads == 1 else STATION_B
        return 1, ""


class PilotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.key = base / "trail.key"
        self.db = base / "replay.db"
        create_lab_key(self.key)
        DurableReplayWindow.initialize(self.db)

    def report(self, seq=1, *, clock=1000.0, missing_retries=False):
        runner = FakeRunner(missing_retries=missing_retries)
        packet = collect_signed_radio(
            interface="wlan0", site_id="lab", node_id="relay",
            peer_id="base", key_id="relay-key", key_file=self.key,
            sequence=seq, runner=runner, sleeper=lambda _: None,
            clock=lambda: clock, observation_id=f"radio-{seq}")
        return packet, runner

    def accept(self, packet, *, db=None, key=None, now=1001.0, node="relay"):
        return receive_signed_radio(packet, site_id="lab", node_id=node,
                                    key_id="relay-key", key_file=key or self.key,
                                    replay_db=db or self.db, now_s=now)

    def test_key_provision_random_and_private(self):
        self.assertEqual(len(read_lab_key(self.key)), 32)
        second = Path(self.temp.name) / "different.key"
        create_lab_key(second)
        self.assertNotEqual(read_lab_key(self.key), read_lab_key(second))
        if os.name == "posix":
            self.assertEqual(self.key.stat().st_mode & 0o077, 0)

    def test_key_no_overwrite(self):
        original = read_lab_key(self.key)
        with self.assertRaises(FileExistsError):
            create_lab_key(self.key)
        self.assertEqual(read_lab_key(self.key), original)

    def test_key_symlink_refused(self):
        link = Path(self.temp.name) / "link.key"
        try:
            link.symlink_to(self.key)
        except OSError:
            self.skipTest("symlinks not supported")
        with self.assertRaises(ValueError):
            read_lab_key(link)

    def test_key_wrong_permissions_refused(self):
        if os.name != "posix":
            self.skipTest("POSIX-only file permissions")
        self.key.chmod(0o644)
        with self.assertRaises(PermissionError):
            read_lab_key(self.key)

    def test_missing_ledger_cannot_initialize_implicitly(self):
        missing = Path(self.temp.name) / "missing.db"
        with self.assertRaises(FileNotFoundError):
            DurableReplayWindow(missing)

    def test_ledger_no_overwrite(self):
        with self.assertRaises(FileExistsError):
            DurableReplayWindow.initialize(self.db)

    def test_ledger_missing_after_accept_refuses_restart(self):
        packet, _ = self.report()
        self.assertEqual(self.accept(packet)["status"], "ACCEPTED_ADVISORY_ONLY")
        self.db.unlink()
        with self.assertRaises(FileNotFoundError):
            DurableReplayWindow(self.db)
        with self.assertRaises(FileNotFoundError):
            self.accept(packet)

    def test_ledger_schema_wrong_refused(self):
        self.db.unlink()
        with sqlite3.connect(str(self.db)) as db:
            db.execute("CREATE TABLE fake (a TEXT)")
        self.db.chmod(0o600)
        with self.assertRaises(ValueError):
            DurableReplayWindow(self.db)

    def test_replay_refused_after_process_like_reopen(self):
        packet, runner = self.report()
        self.assertEqual(self.accept(packet)["status"], "ACCEPTED_ADVISORY_ONLY")
        # A fresh object/connection with same DB must preserve the replay refusal.
        replay = self.accept(packet)
        self.assertEqual(replay["status"], "HOLD")
        self.assertEqual(replay["reason"], "REPLAY_OR_LEDGER_EXHAUSTED")
        self.assertEqual(len(runner.calls), 4)

    def test_both_nodes_receipt_has_zero_authority(self):
        packet, _ = self.report()
        result = self.accept(packet)
        self.assertEqual(result["status"], "ACCEPTED_ADVISORY_ONLY")
        self.assertFalse(result["networkChangeAllowed"])
        self.assertFalse(result["roverMotionAllowed"])
        self.assertFalse(result["fieldIdentityAttested"])
        self.assertFalse(result["radioMeasurementAttested"])
        self.assertFalse(result["networkTransportEstablished"])
        r = result["receipt"]
        self.assertEqual(r["organ"], "sense.radio")
        self.assertFalse(r["mayInvokeTools"])
        self.assertFalse(r["mayIssueHardwareCommands"])
        self.assertFalse(r["somaRuntimeWired"])
        self.assertNotIn("HiddenCampNetwork", json.dumps(result))

    def test_sequence_monotonic_across_reopen(self):
        self.assertEqual(self.accept(self.report(2)[0])["status"], "ACCEPTED_ADVISORY_ONLY")
        self.assertEqual(self.accept(self.report(1)[0])["reason"], "REPLAY_OR_LEDGER_EXHAUSTED")
        self.assertEqual(self.accept(self.report(3)[0])["status"], "ACCEPTED_ADVISORY_ONLY")

    def test_duplicate_observation_id_refused(self):
        self.assertEqual(self.accept(self.report(1)[0])["status"], "ACCEPTED_ADVISORY_ONLY")
        packet, _ = self.report(2)
        packet["observation_id"] = "radio-1"
        # Need valid HMAC, otherwise the duplicate is rejected earlier.
        from trailcore.soma_observation import canonical_json
        import hmac
        body = {k: v for k, v in packet.items() if k != "signature"}
        packet["signature"]["mac_hex"] = hmac.new(read_lab_key(self.key), canonical_json(body), "sha256").hexdigest()
        self.assertEqual(self.accept(packet)["reason"], "REPLAY_OR_LEDGER_EXHAUSTED")

    def test_bad_mac_no_sequence_consumption(self):
        packet, _ = self.report()
        altered = copy.deepcopy(packet)
        altered["measurement"]["retry_pct"] = 21
        self.assertEqual(self.accept(altered)["reason"], "MAC_MISMATCH")
        self.assertEqual(self.accept(packet)["status"], "ACCEPTED_ADVISORY_ONLY")

    def test_wrong_device_binding_fails(self):
        packet, _ = self.report()
        self.assertEqual(self.accept(packet, node="another-node")["reason"], "UNPROVISIONED_PEER")

    def test_wrong_shared_key_fails(self):
        packet, _ = self.report()
        other = Path(self.temp.name) / "other.key"
        create_lab_key(other)
        self.assertEqual(self.accept(packet, key=other)["reason"], "MAC_MISMATCH")

    def test_stale_after_long_manual_transfer_refuses(self):
        packet, _ = self.report()
        self.assertEqual(self.accept(packet, now=1100)["reason"], "STALE_OR_INVALID_TIME")

    def test_missing_counters_never_signs(self):
        packet, runner = self.report(missing_retries=True)
        self.assertIsNone(packet)
        self.assertEqual(len(runner.calls), 4)

    def test_signing_broken_input_holds(self):
        self.assertIsNone(sign_complete_radio_report({}, site_id="lab", node_id="relay",
            peer_id="base", key_id="relay-key", secret=read_lab_key(self.key),
            sequence=1, observation_id="abc"))

    def test_local_packet_file_roundtrip_and_no_overwrite(self):
        packet, _ = self.report()
        path = Path(self.temp.name) / "message.json"
        write_private_json(path, packet)
        self.assertEqual(read_packet_file(path), packet)
        with self.assertRaises(FileExistsError):
            write_private_json(path, packet)

    def test_packet_file_rejects_duplicate_keys(self):
        path = Path(self.temp.name) / "bad.json"
        path.write_text('{"contract":1,"contract":2}')
        if os.name == "posix":
            path.chmod(0o600)
        with self.assertRaises(ValueError):
            read_packet_file(path)

    def test_packet_file_rejects_nan(self):
        path = Path(self.temp.name) / "badnan.json"
        path.write_text('{"x":NaN}')
        if os.name == "posix":
            path.chmod(0o600)
        with self.assertRaises(ValueError):
            read_packet_file(path)

    def test_packet_file_refuses_symlink(self):
        packet, _ = self.report()
        path = Path(self.temp.name) / "good.json"
        write_private_json(path, packet)
        link = Path(self.temp.name) / "link.json"
        try:
            link.symlink_to(path)
        except OSError:
            self.skipTest("symlinks not supported")
        with self.assertRaises(ValueError):
            read_packet_file(link)

    def test_packet_file_refuses_world_readable(self):
        if os.name != "posix":
            self.skipTest("POSIX-only file permissions")
        path = Path(self.temp.name) / "good.json"
        write_private_json(path, self.report()[0])
        path.chmod(0o644)
        with self.assertRaises(PermissionError):
            read_packet_file(path)

    def test_concurrent_same_packet_one_acceptance(self):
        packet, _ = self.report()
        results = []
        lock = threading.Lock()
        def worker():
            outcome = self.accept(packet)
            with lock:
                results.append(outcome["status"])
        threads = [threading.Thread(target=worker) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=4)
        self.assertEqual(len(results), 5)
        self.assertEqual(results.count("ACCEPTED_ADVISORY_ONLY"), 1)
        self.assertEqual(results.count("HOLD"), 4)

    def test_ledger_capacity_fail_closed(self):
        limited = DurableReplayWindow(self.db, max_records=1)
        v = SomaIntake({"relay-key": KeyBinding("lab", "relay", read_lab_key(self.key))},
                       replay=limited)
        self.assertEqual(v.receive(self.report(1)[0], now_s=1001)["status"], "ACCEPTED_ADVISORY_ONLY")
        self.assertEqual(v.receive(self.report(2)[0], now_s=1001)["reason"], "REPLAY_OR_LEDGER_EXHAUSTED")

    def test_cli_keygen_and_init_ledger_error_no_overwrite(self):
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(["keygen", "--key-file", str(self.key)])
        self.assertEqual(status, 2)
        self.assertEqual(json.loads(output.getvalue())["status"], "HOLD")
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(["init-ledger", "--replay-db", str(self.db)])
        self.assertEqual(status, 2)
        self.assertEqual(json.loads(output.getvalue())["status"], "HOLD")

    def test_cli_receive_refuses_replay_without_dumping_packet(self):
        packet, _ = self.report()
        path = Path(self.temp.name) / "packet.json"
        write_private_json(path, packet)
        args = ["receive", "--input", str(path), "--site-id", "lab",
                "--node-id", "relay", "--key-id", "relay-key",
                "--key-file", str(self.key), "--replay-db", str(self.db)]
        out = io.StringIO()
        with redirect_stdout(out):
            status = main(args)
        # Deliberate epoch 1000 fixture is stale against the real clock.
        self.assertEqual(status, 2)
        self.assertEqual(json.loads(out.getvalue())["reason"], "STALE_OR_INVALID_TIME")
        self.assertNotIn("HiddenCampNetwork", out.getvalue())


if __name__ == "__main__":
    unittest.main()
