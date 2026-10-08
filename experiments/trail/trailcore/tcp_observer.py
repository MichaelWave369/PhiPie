"""PhiPie Trail bounded TCP iperf3 client: explicitly opt-in, no server setup.

This performs a short, single-stream TCP upload test to an operator-owned
private IPv4 endpoint using a SOFT iperf3 1 Mbit/s pacing target. It does
NOT guarantee a hard wire-rate cap or prove a Wi-Fi route, and never changes
radio, router, firewall, service configuration, or rover state.
"""
from __future__ import annotations

from hashlib import sha256
import json
import math
import shutil
import subprocess
from typing import Any

from .linux_radio import _private_ipv4
from .soma_observation import canonical_json

SCHEMA = "phipie-trail-bounded-tcp-observation/v0.1"
COMMAND = "iperf3"
MAX_STDOUT = 32_768
PORT = 5201
TEST_SECONDS = 3
TARGET_RATE_BPS = 1_000_000
TIMEOUT_SECONDS = 8


def _number(v: Any, low: float, high: float) -> bool:
    if type(v) not in (float, int):
        return False
    try:
        return math.isfinite(v) and low <= v <= high
    except (ValueError, TypeError, OverflowError):
        return False


def _hold(reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA, "status": "HOLD", "reason": reason,
        "network_change_authorized": False,
        "rover_motion_authorized": False,
        "physical_deployment_authorized": False,
        "hardware_qualified": False,
    }


def command(target: str) -> tuple[str, ...]:
    if not _private_ipv4(target):
        raise ValueError("target must be RFC1918 or permitted private IPv4")
    # -b is an application pacing target, not hard enforced network QoS.
    return ("iperf3", "-4", "-c", target, "-p", str(PORT), "-t", str(TEST_SECONDS),
            "-b", "1M", "-P", "1", "-J")


class Iperf3Runner:
    """Allowlisted client ONLY, no shell, no server, fixed one flow and duration."""
    def run(self, argv: tuple[str, ...], timeout_s: float = TIMEOUT_SECONDS) -> tuple[int, str]:
        if (len(argv) != 13 or argv != command(argv[3])
            or timeout_s != TIMEOUT_SECONDS):
            raise ValueError("unapproved iperf3 invocation")
        exe = shutil.which(COMMAND)
        if exe is None:
            raise FileNotFoundError(COMMAND)
        done = subprocess.run((exe, *argv[1:]), check=False, capture_output=True,
                              text=True, timeout=timeout_s)
        if len(done.stdout) > MAX_STDOUT:
            raise ValueError("oversized iperf3 report")
        return done.returncode, done.stdout


def _parse_report(report: Any) -> dict[str, Any] | None:
    if not isinstance(report, dict) or report.get("error") is not None:
        return None
    start = report.get("start")
    end = report.get("end")
    if not isinstance(start, dict) or not isinstance(end, dict):
        return None
    setup = start.get("test_start")
    sent, received = end.get("sum_sent"), end.get("sum_received")
    if not isinstance(setup, dict) or not isinstance(sent, dict) or not isinstance(received, dict):
        return None
    # Refuse mismatched command/summary. Results can still be fabricated
    # by a compromised local process; this is shape+arithmetic only.
    if (setup.get("protocol") != "TCP"
        or setup.get("duration") != TEST_SECONDS
        or setup.get("num_streams") != 1
        or setup.get("target_bitrate") != TARGET_RATE_BPS):
        return None
    bs, br = sent.get("bytes"), received.get("bytes")
    ts, tr = sent.get("seconds"), received.get("seconds")
    ss, rr = sent.get("bits_per_second"), received.get("bits_per_second")
    if (type(bs) is not int or type(br) is not int
        or not 1 <= br <= bs <= 1_500_000
        or not _number(ts, 1, 6) or not _number(tr, 1, 6)
        or not _number(ss, 1, 3_000_000) or not _number(rr, 1, 3_000_000)
        or abs(ss - (8 * bs / ts)) > max(100_000, ss * .2)
        or abs(rr - (8 * br / tr)) > max(100_000, rr * .2)):
        return None
    retransmits = sent.get("retransmits", None)
    if retransmits is not None and (type(retransmits) is not int or not 0 <= retransmits <= 1_000_000):
        return None
    return {
        "sent_bytes": bs, "received_bytes": br,
        "duration_sent_s": round(float(ts), 5),
        "duration_received_s": round(float(tr), 5),
        "sent_mbps": round(ss / 1_000_000, 5),
        "received_mbps": round(rr / 1_000_000, 5),
        "retransmits": retransmits,
    }


def observe_tcp(target: str, *, approved: bool, runner: Any = None) -> dict[str, Any]:
    """One authorized bounded TCP test; no traffic unless approved.

    A remote iperf3 server must already be started separately by the operator.
    Neither this function nor the CLI provides any server launch action.
    """
    if not approved:
        return _hold("OPERATOR_APPROVAL_REQUIRED")
    try:
        argv = command(target)
    except (ValueError, TypeError):
        return _hold("NONPRIVATE_OR_INVALID_TARGET")
    runner = runner or Iperf3Runner()
    try:
        status, data = runner.run(argv, timeout_s=TIMEOUT_SECONDS)
        if type(status) is not int or status != 0 or not isinstance(data, str) or len(data) > MAX_STDOUT:
            return _hold("IPERF3_UNAVAILABLE_OR_FAILED")
        parsed = json.loads(data, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        metrics = _parse_report(parsed)
        if metrics is None:
            return _hold("TCP_REPORT_INCOMPLETE_OR_INCONSISTENT")
    except (OSError, ValueError, TypeError, OverflowError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return _hold("IPERF3_UNAVAILABLE_OR_FAILED")
    result = {
        "schema": SCHEMA,
        "status": "LOCAL_TCP_OBSERVED",
        "reason": None,
        "target": target,
        "metrics": metrics,
        "limits": {
            "port": PORT, "configured_seconds": TEST_SECONDS,
            "pacing_target_bps": TARGET_RATE_BPS,
            "pacing_is_hard_cap": False,
            "one_stream_only": True,
        },
        "provenance": {
            "source": "operator-approved-iperf3-client",
            "client_report_only": True,
            "server_identity_attested": False,
            "network_interface_bound": False,
            "route_proven": False,
            "traffic_generated": True,
        },
        "network_change_authorized": False,
        "rover_motion_authorized": False,
        "physical_deployment_authorized": False,
        "hardware_qualified": False,
    }
    result["evidence_sha256"] = sha256(canonical_json(result)).hexdigest()
    return result
