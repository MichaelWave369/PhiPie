"""PR19 TCP local observation and additive nine-file binding, fake subprocesses."""
import copy
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from test_probe_bundle import ProbeBundleTests
from trailcore.tcp_observer import (
    Iperf3Runner, _parse_report, command, observe_tcp,
)
from trailcore.tcp_bundle import (
    tcp_manifest_template, verify_tcp_bundle, valid_tcp_record,
)
from trailcore.tcp_cli import main as tcp_main
from trailcore.tcp_bundle_cli import main as binder_main
from trailcore.two_node_pilot import read_packet_file, write_private_json


def fake_report(received=286000):
    return {
        "start": {
            "test_start": {
                "protocol": "TCP", "duration": 3,
                "num_streams": 1, "target_bitrate": 1000000,
            },
        },
        "end": {
            "sum_sent": {
                "seconds": 3.0, "bytes": 300000,
                "bits_per_second": 800000, "retransmits": 2,
            },
            "sum_received": {
                "seconds": 3.0, "bytes": received,
                "bits_per_second": received * 8 / 3.0,
            },
        },
    }


class FakeRunner:
    def __init__(self, raw=None, rc=0):
        self.calls = []
        self.raw = raw or json.dumps(fake_report())
        self.rc = rc

    def run(self, argv, timeout_s=8):
        self.calls.append((argv,timeout_s))
        return self.rc, self.raw


class TcpObserverTests(unittest.TestCase):
    def test_default_denies_without_running(self):
        runner=FakeRunner()
        result=observe_tcp("192.168.1.20",approved=False,runner=runner)
        self.assertEqual(result["status"],"HOLD")
        self.assertEqual(runner.calls,[])

    def test_private_only(self):
        for target in ("8.8.8.8","localhost","127.0.0.1","0.0.0.0",
                       "192.168.1.20;reboot","2001:db8::1","example.org",None):
            runner=FakeRunner()
            with self.subTest(target=target):
                self.assertEqual(observe_tcp(target,approved=True,runner=runner)["status"],"HOLD")
                self.assertEqual(runner.calls,[])

    def test_positive_bounded_client(self):
        runner=FakeRunner()
        result=observe_tcp("192.168.1.20",approved=True,runner=runner)
        self.assertEqual(result["status"],"LOCAL_TCP_OBSERVED")
        self.assertEqual(runner.calls[0][0],command("192.168.1.20"))
        self.assertEqual(runner.calls[0][1],8)
        self.assertAlmostEqual(result["metrics"]["received_mbps"],.76266667,places=4)
        self.assertFalse(result["limits"]["pacing_is_hard_cap"])
        self.assertFalse(result["provenance"]["server_identity_attested"])
        self.assertFalse(result["provenance"]["network_interface_bound"])
        self.assertFalse(result["network_change_authorized"])
        self.assertFalse(result["hardware_qualified"])
        self.assertNotIn("start",result)
        self.assertEqual(len(result["evidence_sha256"]),64)

    def test_transport_failure(self):
        self.assertEqual(observe_tcp("192.168.1.20",approved=True,
                                     runner=FakeRunner(rc=1))["status"],"HOLD")

    def test_invalid_json(self):
        self.assertEqual(observe_tcp("192.168.1.20",approved=True,
                                     runner=FakeRunner(raw="{broken"))["status"],"HOLD")

    def test_json_nan_rejected(self):
        self.assertEqual(observe_tcp("192.168.1.20",approved=True,
                                     runner=FakeRunner(raw='{"value":NaN}'))["status"],"HOLD")

    def test_oversized_output(self):
        self.assertEqual(observe_tcp("192.168.1.20",approved=True,
                                     runner=FakeRunner(raw="z"*40000))["status"],"HOLD")

    def test_wrong_protocol_duration_streams_bitrate(self):
        for key,value in (("protocol","UDP"),("duration",30),
                          ("num_streams",4),("target_bitrate",0)):
            data=fake_report()
            data["start"]["test_start"][key]=value
            with self.subTest(key=key):
                self.assertIsNone(_parse_report(data))

    def test_report_error_rejected(self):
        data=fake_report()
        data["error"]="connection refused"
        self.assertIsNone(_parse_report(data))

    def test_impossible_byte_accounting(self):
        for rec in (0,400000,2_000_000):
            self.assertIsNone(_parse_report(fake_report(rec)))

    def test_number_pathologies(self):
        for value in (None,True,float("nan"),10**1000):
            data=fake_report()
            data["end"]["sum_received"]["seconds"]=value
            with self.subTest(value=str(value)[:30]):
                self.assertIsNone(_parse_report(data))

    def test_missing_result_fields(self):
        self.assertIsNone(_parse_report({}))
        data=fake_report(); data["end"].pop("sum_received")
        self.assertIsNone(_parse_report(data))

    def test_invalid_retransmits(self):
        data=fake_report(); data["end"]["sum_sent"]["retransmits"]=-1
        self.assertIsNone(_parse_report(data))

    def test_runner_rejects_server_and_unbounded(self):
        runner=Iperf3Runner()
        for argv in (("iperf3","-s"),("iperf3","-c","8.8.8.8","-t","100"),
                     ("iperf3","-4","-c","192.168.1.20","-t","300")):
            with self.subTest(argv=argv), self.assertRaises(ValueError):
                runner.run(argv)

    def test_cli_requires_approval_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"x.json"
            output=io.StringIO()
            with redirect_stdout(output):
                status=tcp_main(["--target","192.168.1.20","--output",str(p)])
            self.assertEqual(status,2)
            self.assertFalse(p.exists())
            self.assertIn("OPERATOR_APPROVAL_REQUIRED",output.getvalue())

    def test_cli_writes_private_file_only_after_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"tcp.json"
            report=observe_tcp("192.168.1.20",approved=True,runner=FakeRunner())
            with patch("trailcore.tcp_cli.observe_tcp",return_value=report):
                out=io.StringIO()
                with redirect_stdout(out):
                    status=tcp_main(["--target","192.168.1.20",
                                     "--approve-tcp","--output",str(p)])
            self.assertEqual(status,0)
            self.assertEqual(read_packet_file(p),report)
            self.assertNotIn("192.168.1.20",out.getvalue())
            if os.name=="posix":
                self.assertEqual(p.stat().st_mode&0o077,0)

    def test_cli_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"tcp.json"
            report=observe_tcp("192.168.1.20",approved=True,runner=FakeRunner())
            write_private_json(p,report)
            with patch("trailcore.tcp_cli.observe_tcp",return_value=report):
                with redirect_stdout(io.StringIO()):
                    status=tcp_main(["--target","192.168.1.20",
                                     "--approve-tcp","--output",str(p)])
            self.assertEqual(status,2)


class TcpBundleTests(unittest.TestCase):
    def setUp(self):
        self.base=ProbeBundleTests("test_complete_local_probe_pair_still_non_qualifying")
        self.base.setUp()
        self.addCleanup(self.base.doCleanups)
        self.manifest=tcp_manifest_template()
        self.observation=observe_tcp("192.168.1.20",approved=True,runner=FakeRunner())
        write_private_json(self.base.private / self.manifest["files"]["tcp_observation"],
                           self.observation)

    def check(self):
        return verify_tcp_bundle(self.base.witness,self.manifest,self.base.private)

    def rewrite(self,observation):
        p=self.base.private / self.manifest["files"]["tcp_observation"]
        p.unlink()
        write_private_json(p,observation)

    def test_nine_consistent_files_advisory_only(self):
        result=self.check()
        self.assertEqual(result["status"],"LOCAL_TCP_EVIDENCE_MATCH")
        self.assertEqual(len(result["checks"]),9)
        self.assertTrue(all(v=="MATCH" for v in result["checks"].values()))
        self.assertAlmostEqual(result["reported_receiver_mbps"],.76267,places=4)
        for k in ("hardware_qualified","physical_hardware_qualified",
                  "actual_link_path_verified","mesh_transport_verified",
                  "receiver_identity_attested","end_to_end_capacity_qualified",
                  "hard_rate_limit_guaranteed","network_change_authorized",
                  "rover_motion_authorized","physical_deployment_authorized"):
            self.assertFalse(result[k],k)

    def test_previous_eight_file_baseline_still_available(self):
        from trailcore.probe_bundle import verify_probe_bundle, probe_manifest_template
        eight=probe_manifest_template()
        result=verify_probe_bundle(self.base.witness,eight,self.base.private)
        self.assertEqual(result["status"],"LOCAL_PROBE_EVIDENCE_MATCH")

    def test_tampered_rate_refused(self):
        altered=copy.deepcopy(self.observation)
        altered["metrics"]["received_mbps"]=100.0
        self.rewrite(altered)
        self.assertIn("TCP_EVIDENCE_MISMATCH",self.check()["reasons"])

    def test_fake_hard_cap_refused(self):
        altered=copy.deepcopy(self.observation)
        altered["limits"]["pacing_is_hard_cap"]=True
        self.rewrite(altered)
        self.assertEqual(self.check()["status"],"HOLD")

    def test_fake_server_attestation_refused(self):
        altered=copy.deepcopy(self.observation)
        altered["provenance"]["server_identity_attested"]=True
        self.rewrite(altered)
        self.assertEqual(self.check()["status"],"HOLD")

    def test_missing_tcp_file_refused(self):
        (self.base.private/self.manifest["files"]["tcp_observation"]).unlink()
        self.assertIn("TCP_UNREADABLE_OR_UNSAFE",self.check()["reasons"])

    def test_missing_icmp_file_refused(self):
        (self.base.private/self.manifest["files"]["icmp_probe"]).unlink()
        self.assertIn("EIGHT_FILE_BASELINE_HOLD",self.check()["reasons"])

    def test_unsafe_manifest_path_refused(self):
        self.manifest["files"]["tcp_observation"]="../../key.hex"
        self.assertIn("INVALID_TCP_MANIFEST",self.check()["reasons"])

    def test_duplicate_filenames_refused(self):
        self.manifest["files"]["tcp_observation"]=self.manifest["files"]["icmp_probe"]
        self.assertIn("INVALID_TCP_MANIFEST",self.check()["reasons"])

    def test_symlink_tcp_file_refused(self):
        p=self.base.private/self.manifest["files"]["tcp_observation"]
        backup=self.base.private/"original-tcp.json"
        p.rename(backup)
        try:
            p.symlink_to(backup)
        except OSError:
            self.skipTest("symlinks unsupported")
        self.assertEqual(self.check()["status"],"HOLD")

    def test_consistent_files_do_not_expose_target(self):
        output=json.dumps(self.check())
        self.assertNotIn("192.168.1.20",output)
        self.assertNotIn("SecretForestNetwork",output)
        self.assertNotIn(str(self.base.private),output)

    def test_no_tcp_handoff_grants_soma_authority(self):
        self.assertIs(self.check()["network_change_authorized"],False)
        self.assertIs(self.check()["physical_deployment_authorized"],False)

    def test_legacy_witness_simulation_refused(self):
        self.base.witness["mode"]="LAB_SIMULATION"
        self.assertEqual(self.check()["status"],"HOLD")

    def test_tcp_report_requires_all_fields(self):
        altered=copy.deepcopy(self.observation)
        altered["provenance"].pop("route_proven")
        self.assertFalse(valid_tcp_record(altered))

    def test_cli_nine_slot_manifest(self):
        self.assertEqual(len(tcp_manifest_template()["files"]),9)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"manifest.json"
            with redirect_stdout(io.StringIO()):
                status=binder_main(["manifest","--output",str(p)])
            self.assertEqual(status,0)
            self.assertEqual(len(read_packet_file(p)["files"]),9)

    def test_cli_inspect_private_nine_file_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)
            w=path/"witness.json"; m=path/"manifest.json"; o=path/"out.json"
            write_private_json(w,self.base.witness)
            write_private_json(m,self.manifest)
            with redirect_stdout(io.StringIO()):
                status=binder_main(["inspect","--witness",str(w),"--manifest",str(m),
                                    "--evidence-dir",str(self.base.private),"--output",str(o)])
            self.assertEqual(status,0)
            self.assertEqual(read_packet_file(o)["status"],"LOCAL_TCP_EVIDENCE_MATCH")


if __name__=="__main__":
    unittest.main()
