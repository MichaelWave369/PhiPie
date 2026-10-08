"""Offline Linux radio observer contract tests. No real radio or ICMP traffic."""
import copy
import hmac
import json
import unittest
from unittest.mock import patch
from trailcore import linux_radio as rf
from trailcore.soma_observation import KeyBinding, SomaIntake, canonical_json


DEV = """phy#0
    Interface wlan0
        ifindex 3
        wdev 0x1
        addr 00:11:22:33:44:55
        type managed
    Interface wlan1
        type AP
"""
LINK = """Connected to aa:bb:cc:dd:ee:ff (on wlan0)
    SSID: PrivateForest
    freq: 2412
    RX: 111 bytes (4 packets)
    TX: 222 bytes (5 packets)
    signal: -63 dBm
    tx bitrate: 72.2 MBit/s MCS 7
"""
STATION_1 = """Station aa:bb:cc:dd:ee:ff (on wlan0)
    inactive time: 10 ms
    tx packets: 100
    tx retries: 4
"""
STATION_2 = """Station aa:bb:cc:dd:ee:ff (on wlan0)
    tx packets: 112
    tx retries: 7
"""
PING = """PING 192.168.1.1 (192.168.1.1) 56(84) bytes of data.
64 bytes from 192.168.1.1: icmp_seq=1 ttl=64 time=7.2 ms
64 bytes from 192.168.1.1: icmp_seq=2 ttl=64 time=10.1 ms
64 bytes from 192.168.1.1: icmp_seq=3 ttl=64 time=8.0 ms
--- 192.168.1.1 ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2000ms
rtt min/avg/max/mdev = 7.200/8.433/10.100/1.240 ms
"""


class FakeRunner:
    def __init__(self, overrides=None):
        self.calls = []
        self.station_reads = 0
        self.overrides = overrides or {}

    def run(self, argv, timeout_s=3.0):
        self.calls.append(tuple(argv))
        if tuple(argv) in self.overrides:
            custom = self.overrides[tuple(argv)]
            if isinstance(custom, Exception):
                raise custom
            return custom
        if argv == ("iw", "dev"):
            return 0, DEV
        if argv == ("iw", "dev", "wlan0", "link"):
            return 0, LINK
        if argv == ("iw", "dev", "wlan0", "station", "dump"):
            self.station_reads += 1
            return 0, STATION_1 if self.station_reads == 1 else STATION_2
        if argv == ("ping", "-n", "-I", "wlan0", "-c", "3", "-W", "1", "192.168.1.1"):
            return 0, PING
        return 1, ""


def sample(runner=None):
    return rf.observe_radio("wlan0", runner=runner or FakeRunner(),
                            sleeper=lambda _: None, clock=lambda: 1001.0)


class LinuxRadioObserverTests(unittest.TestCase):
    def test_interface_discovery_filters_mac_and_ssid(self):
        r = rf.list_radios(FakeRunner())
        self.assertEqual(r["status"], "OBSERVED")
        self.assertEqual(r["interfaces"], ["wlan0", "wlan1"])
        self.assertNotIn("00:11:22", json.dumps(r))

    def test_full_sample_metric_integrity(self):
        r = sample()
        self.assertEqual(r["status"], "COMPLETE")
        self.assertEqual(r["metrics"]["rssi_dbm"], -63)
        self.assertEqual(r["metrics"]["tx_phy_mbps"], 72.2)
        self.assertEqual(r["metrics"]["frequency_mhz"], 2412)
        self.assertEqual(r["metrics"]["retry_pct"], 20.0)
        self.assertEqual(r["metrics"]["sample_count"], 15)
        self.assertTrue(r["provenance"]["tx_phy_is_not_throughput"])
        self.assertFalse(r["network_change_authority"])
        self.assertEqual(len(r["evidence_sha256"]), 64)
        self.assertNotIn("PrivateForest", json.dumps(r))
        self.assertNotIn("aa:bb:cc", json.dumps(r))

    def test_no_interface_holds(self):
        runner = FakeRunner({("iw", "dev"): (0, "")})
        self.assertEqual(sample(runner)["reason"], "INTERFACE_NOT_DISCOVERED")

    def test_unsupported_iw_holds(self):
        runner = FakeRunner({("iw", "dev"): FileNotFoundError("iw")})
        self.assertEqual(sample(runner)["reason"], "INTERFACE_NOT_DISCOVERED")

    def test_disconnected_refuses(self):
        runner = FakeRunner({("iw", "dev", "wlan0", "link"): (0, "Not connected.")})
        self.assertEqual(sample(runner)["reason"], "LINK_UNAVAILABLE")

    def test_missing_retries_never_fabricated(self):
        runner = FakeRunner({("iw", "dev", "wlan0", "station", "dump"): (0, "")})
        r = sample(runner)
        self.assertEqual(r["status"], "PARTIAL")
        self.assertIsNone(r["metrics"]["retry_pct"])
        self.assertIsNone(rf.make_soma_radio_unsigned(r, site_id="lab", node_id="relay",
                              peer_id="base", observation_id="a1", sequence=1))

    def test_missing_signal_holds_admission(self):
        runner = FakeRunner({("iw", "dev", "wlan0", "link"): (0, "tx bitrate: 54.0 MBit/s\n")})
        self.assertEqual(sample(runner)["status"], "PARTIAL")

    def test_multiple_stations_no_aggregate(self):
        data = STATION_1 + STATION_1
        runner = FakeRunner({("iw", "dev", "wlan0", "station", "dump"): (0, data)})
        self.assertIsNone(sample(runner)["metrics"]["retry_pct"])

    def test_station_counter_reset_no_retry_estimate(self):
        runner = FakeRunner()
        def station(seq):
            return (0, STATION_1 if seq == 1 else
                    "Station aa:bb:cc:dd:ee:ff (on wlan0)\n    tx packets: 90\n    tx retries: 0\n")
        runner.overrides[("iw", "dev", "wlan0", "station", "dump")] = (0, "")
        self.assertEqual(sample(runner)["status"], "PARTIAL")

    def test_stale_time_refused(self):
        r = rf.observe_radio("wlan0", runner=FakeRunner(),
                             sleeper=lambda _: None, clock=lambda: float("nan"))
        self.assertEqual(r["reason"], "INVALID_OBSERVATION_TIME")

    def test_bad_ifname_never_executes(self):
        runner = FakeRunner()
        r = rf.observe_radio("wlan0;shutdown", runner=runner)
        self.assertEqual(r["status"], "HOLD")
        self.assertEqual(runner.calls, [])

    def test_opt_in_ping(self):
        runner = FakeRunner()
        r = rf.observe_ping("192.168.1.1", "wlan0", approved=True, runner=runner)
        self.assertEqual(r["status"], "OBSERVED_ADVISORY_ONLY")
        self.assertEqual(r["metrics"]["sent"], 3)
        self.assertAlmostEqual(r["metrics"]["probe_rtt_avg_ms"], 8.433)
        self.assertIsNone(r["metrics"]["observed_mbps"])
        self.assertTrue(r["provenance"]["traffic_generated"])

    def test_no_approval_causes_no_io(self):
        runner = FakeRunner()
        r = rf.observe_ping("192.168.1.1", "wlan0", approved=False, runner=runner)
        self.assertEqual(r["reason"], "OPERATOR_PROBE_APPROVAL_REQUIRED")
        self.assertEqual(runner.calls, [])

    def test_external_ping_target_refused(self):
        for target in ("8.8.8.8", "localhost", "https://example.com", "127.0.0.1",
                       "224.0.0.1", "0.0.0.0", "192.168.1.1;rm"):
            with self.subTest(target=target):
                runner = FakeRunner()
                self.assertEqual(rf.observe_ping(target, "wlan0", approved=True,
                                                  runner=runner)["status"], "HOLD")
                self.assertEqual(runner.calls, [])

    def test_ping_missing_rtt_holds(self):
        cmd = ("ping", "-n", "-I", "wlan0", "-c", "3", "-W", "1", "192.168.1.1")
        runner = FakeRunner({cmd: (1, "3 packets transmitted, 0 received, 100% packet loss")})
        self.assertEqual(rf.observe_ping("192.168.1.1", "wlan0", approved=True,
                                         runner=runner)["reason"], "INSUFFICIENT_PROBE_REPLY")

    def test_ping_inconsistent_holds(self):
        cmd = ("ping", "-n", "-I", "wlan0", "-c", "3", "-W", "1", "192.168.1.1")
        runner = FakeRunner({cmd: (0, PING.replace("0% packet loss", "100% packet loss"))})
        self.assertEqual(rf.observe_ping("192.168.1.1", "wlan0", approved=True,
                                         runner=runner)["reason"], "INCONSISTENT_PROBE_DATA")

    def test_ping_failure_holds(self):
        cmd = ("ping", "-n", "-I", "wlan0", "-c", "3", "-W", "1", "192.168.1.1")
        runner = FakeRunner({cmd: TimeoutError("timeout")})
        self.assertEqual(rf.observe_ping("192.168.1.1", "wlan0", approved=True,
                                         runner=runner)["reason"], "PROBE_UNAVAILABLE")

    def test_unapproved_shell_commands_refused(self):
        runner = rf.ReadOnlyCommandRunner()
        for args in (("iw", "dev", "wlan0", "set", "channel", "2"),
                     ("ping", "-c", "100000", "8.8.8.8"),
                     ("sudo", "iw", "dev"),
                     ("iw", "dev", "wlan0;reboot", "link")):
            with self.subTest(args=args), self.assertRaises(ValueError):
                runner.run(args)

    def test_soma_draft_unsigned_never_pretends_authenticated(self):
        r = sample()
        packet = rf.make_soma_radio_unsigned(r, site_id="lab", node_id="relay",
                     peer_id="base", observation_id="obs-1", sequence=1)
        self.assertEqual(packet["organ"], "sense.radio")
        self.assertNotIn("signature", packet)
        self.assertEqual(packet["measurement"]["retry_pct"], 20)
        self.assertFalse(packet["authority"]["actionAuthorized"])
        self.assertFalse(packet["authority"]["mayIssueHardwareCommands"])
        self.assertEqual(SomaIntake({"k": KeyBinding("lab", "relay", bytes(range(32)))})
                          .receive(packet, now_s=1001)["status"], "REFUSED")

    def test_soma_signed_lab_handoff_does_not_grant_tools(self):
        packet = rf.make_soma_radio_unsigned(sample(), site_id="lab", node_id="relay",
                     peer_id="base", observation_id="obs-1", sequence=1)
        secret = bytes(range(32))
        packet["signature"] = {"alg": "HMAC-SHA256", "key_id": "lab-key",
             "mac_hex": hmac.new(secret, canonical_json(packet), "sha256").hexdigest()}
        admitted = SomaIntake({"lab-key": KeyBinding("lab", "relay", secret)}).receive(packet, now_s=1001)
        self.assertEqual(admitted["status"], "ACCEPTED_ADVISORY_ONLY")
        self.assertFalse(admitted["receipt"]["mayInvokeTools"])
        self.assertFalse(admitted["receipt"]["mayIssueHardwareCommands"])
        self.assertFalse(admitted["receipt"]["somaRuntimeWired"])

    def test_soma_peer_alias_not_inferred_from_bssid(self):
        report = sample()
        packet = rf.make_soma_radio_unsigned(report, site_id="lab", node_id="relay",
                   peer_id="base", observation_id="obs-1", sequence=1)
        self.assertEqual(packet["measurement"]["peer_id"], "base")
        self.assertNotIn("aa:bb:cc", json.dumps(packet))

    def test_readonly_failure_from_runner(self):
        runner = FakeRunner({("iw", "dev"): PermissionError("permission denied")})
        self.assertEqual(rf.list_radios(runner)["reason"], "IW_UNAVAILABLE")

    def test_snapshot_oversize_rejected(self):
        runner = FakeRunner({("iw", "dev"): (0, DEV * 10000)})
        self.assertEqual(rf.list_radios(runner)["reason"], "IW_UNAVAILABLE")

    def test_bounded_sampling_time_refused(self):
        runner = FakeRunner()
        r = rf.observe_radio("wlan0", runner=runner, interval_s=900)
        self.assertEqual(r["reason"], "INVALID_OBSERVER_REQUEST")
        self.assertEqual(runner.calls, [])


if __name__ == "__main__":
    unittest.main()
