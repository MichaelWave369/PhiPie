"""PhiPie PR20: operator field launch; all Linux and iw calls are faked."""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from trailcore.field_host import capture_host
from trailcore.field_launch import (
    PREFLIGHT_CONTRACT, SESSION_CONTRACT, collect_local, doctor,
)
from trailcore.field_launch_cli import main
from trailcore.two_node_pilot import read_packet_file

DEV = ("phy#0\n    Interface wlan0\n        addr 12:34:56:78:ab:cd\n"
       "        type managed\n")
LINK = ("Connected to 12:34:56:78:ab:cd (on wlan0)\n"
        "    SSID: SecretOwnerNetwork\n    freq: 2412\n"
        "    signal: -58 dBm\n    tx bitrate: 72.2 MBit/s\n")
STA1 = ("Station 12:34:56:78:ab:cd (on wlan0)\n"
        "    tx packets: 100\n    tx retries: 4\n")
STA2 = ("Station 12:34:56:78:ab:cd (on wlan0)\n"
        "    tx packets: 120\n    tx retries: 6\n")


class Runner:
    def __init__(self, *, no_interface=False, partial=False):
        self.calls = []
        self.no_interface = no_interface
        self.partial = partial
        self.stations = 0

    def run(self, argv, timeout_s=3):
        self.calls.append(argv)
        if argv == ("iw", "dev"):
            return 0, "" if self.no_interface else DEV
        if argv == ("iw", "dev", "wlan0", "link"):
            return 0, LINK
        if argv == ("iw", "dev", "wlan0", "station", "dump"):
            self.stations += 1
            return (0, "") if self.partial else (
                0, STA1 if self.stations == 1 else STA2
            )
        raise AssertionError("unexpected tool invocation")


def pi_host(model="Raspberry Pi 5 Model B Rev 1"):
    return capture_host(
        model_text=model, machine="aarch64", kernel="6.12.33",
        clock=lambda: 1001.0,
    )


def tool_present(tool):
    return "/usr/bin/" + tool


class FieldLaunchTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.host = pi_host()

    def inspect(self, *, runner=None, host=None, **kwargs):
        return doctor(
            "wlan0", runner=runner if runner is not None else Runner(),
            which=tool_present, system="Linux",
            host=host if host is not None else self.host, **kwargs,
        )

    def collect(self, path=None, *, runner=None, **kwargs):
        return collect_local(
            path or (self.root / "sender-001"),
            role="sender", node_id="relay-a", test_id="trial-001",
            interface="wlan0", runner=runner if runner is not None else Runner(),
            which=tool_present, system="Linux", host=self.host,
            clock=lambda: 1002.0, sleeper=lambda _: None, **kwargs,
        )

    def test_doctor_is_readonly_and_nonqualifying(self):
        runner = Runner()
        r = self.inspect(runner=runner)
        self.assertEqual(r["contract"], PREFLIGHT_CONTRACT)
        self.assertEqual(r["status"], "READY_FOR_READONLY_CAPTURE")
        self.assertEqual(runner.calls, [("iw", "dev")])
        for key in ("network_traffic_generated", "network_change_authorized",
                    "rover_motion_authorized", "physical_hardware_qualified",
                    "site_authority_verified", "remote_transport_established",
                    "operator_identity_verified", "clock_trust_established"):
            self.assertIs(r[key], False, key)

    def test_doctor_does_not_invent_tools_missing(self):
        r = doctor("wlan0", runner=Runner(),
                   which=lambda tool: None if tool == "iperf3" else tool_present(tool),
                   system="Linux", host=self.host)
        self.assertEqual(r["status"], "READY_FOR_READONLY_CAPTURE")
        self.assertFalse(r["tool_executable_found"]["iperf3"])
        self.assertTrue(r["tool_executable_found"]["iw"])

    def test_missing_iw_blocks_capture(self):
        runner = Runner()
        output = doctor("wlan0", runner=runner, which=lambda name: None,
                        system="Linux", host=self.host)
        self.assertEqual(output["status"], "HOLD")
        self.assertIn("IW_TOOL_MISSING", output["reasons"])
        self.assertEqual(runner.calls, [])

    def test_unknown_linux_platform_holds(self):
        r = self.inspect(host=pi_host(model="Generic PC"))
        self.assertEqual(r["status"], "HOLD")
        self.assertIn("PI_FAMILY_NOT_REPORTED", r["reasons"])

    def test_nonlinux_platform_holds(self):
        r = doctor("wlan0", runner=Runner(), which=tool_present,
                   system="Windows", host=self.host)
        self.assertIn("LINUX_REQUIRED", r["reasons"])

    def test_compute_module5_alias_allowed(self):
        r = self.inspect(host=pi_host("Raspberry Pi Compute Module 5 Rev 1"))
        self.assertEqual(r["status"], "READY_FOR_READONLY_CAPTURE")

    def test_invalid_interface_refused_no_commands(self):
        runner = Runner()
        r = doctor("wlan0;reboot", runner=runner, which=tool_present,
                   system="Linux", host=self.host)
        self.assertIn("INVALID_INTERFACE_ALIAS", r["reasons"])
        self.assertEqual(runner.calls, [])

    def test_undiscovered_interface_holds(self):
        runner = Runner(no_interface=True)
        r = self.inspect(runner=runner)
        self.assertIn("WIRELESS_INTERFACE_NOT_DISCOVERED", r["reasons"])
        self.assertEqual(runner.calls, [("iw", "dev")])

    def test_host_record_invalid(self):
        r = self.inspect(host={"schema": "fake"})
        self.assertIn("INVALID_HOST_RECORD", r["reasons"])

    def test_capture_creates_three_private_files(self):
        runner = Runner()
        path = self.root / "sender-001"
        r = self.collect(path=path, runner=runner)
        self.assertEqual(r["status"], "LOCAL_CAPTURE_RECORDED")
        self.assertEqual(set(x.name for x in path.iterdir()),
                         {"host.json", "radio.json", "session.json"})
        self.assertTrue(all(cmd[0] == "iw" for cmd in runner.calls))
        self.assertEqual(len(runner.calls), 5)
        self.assertFalse(r["two_node_field_trial_completed"])
        self.assertFalse(r["physical_hardware_qualified"])
        if os.name == "posix":
            self.assertEqual(path.stat().st_mode & 0o077, 0)
            for f in path.iterdir():
                self.assertEqual(f.stat().st_mode & 0o077, 0)
        session = read_packet_file(path / "session.json")
        host = read_packet_file(path / "host.json")
        radio = read_packet_file(path / "radio.json")
        self.assertEqual(session["contract"], SESSION_CONTRACT)
        self.assertEqual(session["host_snapshot_sha256"], host["snapshot_sha256"])
        self.assertEqual(session["radio_report_sha256"], radio["evidence_sha256"])
        self.assertFalse(session["site_permission_independently_verified"])

    def test_output_never_contains_raw_identifiers(self):
        self.collect()
        contents = "\n".join(p.read_text() for p in (self.root / "sender-001").iterdir())
        self.assertNotIn("SecretOwnerNetwork", contents)
        self.assertNotIn("12:34:56:78:ab:cd", contents)

    def test_partial_radio_stored_but_not_pass(self):
        r = self.collect(runner=Runner(partial=True))
        self.assertEqual(r["status"], "PARTIAL_OR_UNAVAILABLE_RADIO")
        self.assertTrue(r["files_written"])
        self.assertEqual(r["radio_status"], "PARTIAL")
        self.assertIs(r["physical_hardware_qualified"], False)
        radio = read_packet_file(self.root / "sender-001" / "radio.json")
        self.assertIsNone(radio["metrics"]["retry_pct"])

    def test_capture_refused_before_creating_directory(self):
        runner = Runner(no_interface=True)
        r = self.collect(runner=runner)
        self.assertEqual(r["status"], "HOLD")
        self.assertFalse(r["files_written"])
        self.assertFalse((self.root / "sender-001").exists())

    def test_invalid_role_holds(self):
        r = collect_local(
            self.root / "unused", role="pilot", node_id="node-a",
            test_id="trial-001", interface="wlan0")
        self.assertEqual(r["status"], "HOLD")
        self.assertFalse((self.root / "unused").exists())

    def test_invalid_node_identity_holds(self):
        r = collect_local(
            self.root / "unused", role="sender", node_id="../token",
            test_id="trial-001", interface="wlan0")
        self.assertEqual(r["status"], "HOLD")
        self.assertFalse((self.root / "unused").exists())

    def test_invalid_test_id_holds(self):
        r = collect_local(
            self.root / "unused", role="sender", node_id="node",
            test_id="trial id with spaces", interface="wlan0")
        self.assertEqual(r["status"], "HOLD")

    def test_no_overwriting_existing_session(self):
        self.collect()
        with self.assertRaises(ValueError):
            self.collect()
        self.assertEqual(len(list((self.root / "sender-001").iterdir())), 3)

    def test_existing_symlink_session_refused(self):
        destination = self.root / "destination"
        destination.mkdir()
        link = self.root / "sender-001"
        try:
            link.symlink_to(destination)
        except OSError:
            self.skipTest("no symlink support")
        with self.assertRaises(ValueError):
            self.collect()

    def test_parent_directory_symlink_refused(self):
        real = self.root / "real"
        real.mkdir()
        alias = self.root / "alias"
        try:
            alias.symlink_to(real)
        except OSError:
            self.skipTest("no symlink support")
        with self.assertRaises(ValueError):
            self.collect(path=alias / "sender-001")

    def test_missing_parent_refuses_without_creation(self):
        with self.assertRaises(ValueError):
            self.collect(path=self.root / "unknown" / "sender-001")
        self.assertFalse((self.root / "unknown").exists())

    def test_failed_clock_stores_hold_diagnostic(self):
        r = collect_local(
            self.root / "sender-001", role="sender", node_id="relay-a",
            test_id="trial-001", interface="wlan0", runner=Runner(),
            which=tool_present, system="Linux", host=self.host,
            clock=lambda: float("nan"), sleeper=lambda _: None,
        )
        self.assertEqual(r["status"], "PARTIAL_OR_UNAVAILABLE_RADIO")
        self.assertEqual(r["radio_status"], "HOLD")
        report = read_packet_file(self.root / "sender-001" / "radio.json")
        self.assertEqual(report["reason"], "INVALID_OBSERVATION_TIME")

    def test_receiver_side_also_inert(self):
        r = collect_local(
            self.root / "receiver-001", role="receiver", node_id="base-b",
            test_id="trial-001", interface="wlan0", runner=Runner(),
            which=tool_present, system="Linux", host=self.host,
            clock=lambda: 1002.0, sleeper=lambda _: None,
        )
        self.assertEqual(r["status"], "LOCAL_CAPTURE_RECORDED")
        session = read_packet_file(self.root / "receiver-001" / "session.json")
        self.assertEqual(session["node_role"], "receiver")
        self.assertFalse(session["two_node_field_trial_completed"])

    def test_cli_doctor_unsupported_host_fails_closed(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(["doctor", "--interface", "wlan0"])
        self.assertIn(code, (0, 2))
        report = json.loads(out.getvalue())
        self.assertIs(report["physical_hardware_qualified"], False)

    def test_cli_collect_does_not_fabricate_on_ci(self):
        with patch("trailcore.field_launch_cli.collect_local", return_value={
            "status": "HOLD", "reason": "PREFLIGHT_HOLD",
            "files_written": False, "physical_hardware_qualified": False,
        }):
            out = io.StringIO()
            with redirect_stdout(out):
                code = main([
                    "collect", "--interface", "wlan0", "--role", "sender",
                    "--node", "relay-a", "--test-id", "trial-001",
                    "--session-dir", str(self.root / "sender-001"),
                ])
        self.assertEqual(code, 2)
        self.assertFalse((self.root / "sender-001").exists())

    def test_preflight_never_calls_ping_or_iperf(self):
        runner = Runner()
        self.inspect(runner=runner)
        self.collect(path=self.root / "sender-001", runner=runner)
        self.assertTrue(all(cmd[0] == "iw" for cmd in runner.calls))


if __name__ == "__main__":
    unittest.main()
