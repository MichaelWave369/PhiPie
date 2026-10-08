"""PhiPie Trail Linux radio observer v0.1.

Read-only userspace Wi-Fi observations from Linux `iw` and sysfs.
Optional, explicitly approved bounded ICMP probe is separate.

No use of iw set/connect/scan, ip link, routing, AP configuration, motor
controls, raw identifiers, or automatic credential/signature creation.
No PHY-rate-to-throughput substitution; unavailable measurements stay null.
"""
from __future__ import annotations
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from typing import Any, Callable

from .soma_observation import AUTHORITY, CONTRACT, canonical_json

IF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,14}$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")
DEV_IF_RE = re.compile(r"^\s*Interface\s+([A-Za-z0-9_.:-]{1,15})\s*$", re.M)
TYPE_RE = re.compile(r"^\s*type\s+([a-zA-Z0-9_-]+)\s*$", re.M)
SIGNAL_RE = re.compile(r"^\s*signal:\s*(-?\d+(?:\.\d+)?)\s*dBm\s*$", re.M)
BITRATE_RE = re.compile(r"^\s*tx bitrate:\s*(\d+(?:\.\d+)?)\s*MBit/s\b", re.M)
FREQ_RE = re.compile(r"^\s*freq:\s*(\d{3,5})\s*$", re.M)
STATION_RE = re.compile(r"^\s*Station\s+[0-9A-Fa-f:]{17}(?:\s|$)", re.M)
TX_PACKETS_RE = re.compile(r"^\s*tx packets:\s*(\d+)\s*$", re.M)
TX_RETRIES_RE = re.compile(r"^\s*tx retries:\s*(\d+)\s*$", re.M)
PING_STATS_RE = re.compile(r"(\d+) packets transmitted, (\d+) (?:packets )?received, (\d+(?:\.\d+)?)% packet loss")
PING_RTT_RE = re.compile(r"(?:rtt|round-trip) min/avg/max/(?:mdev|stddev) = \d+(?:\.\d+)?/(\d+(?:\.\d+)?)/")

SCHEMA = "phipie-trail-linux-radio-observer/v0.1"
MAX_OUTPUT = 16384


def _id(s: Any, *, iface: bool = False) -> bool:
    return isinstance(s, str) and bool((IF_RE if iface else ID_RE).fullmatch(s))


class ReadOnlyCommandRunner:
    """Restricted command runner; absolute executable paths, no shell or input."""
    def run(self, argv: tuple[str, ...], timeout_s: float = 3.0) -> tuple[int, str]:
        if not argv or argv[0] not in {"iw", "ping"} or not 0 < timeout_s <= 6:
            raise ValueError("unapproved command")
        # Guard the low-level execution surface independently from its callers.
        if argv[0] == "iw":
            permitted = (argv == ("iw", "dev") or
                         (len(argv) == 4 and argv[1] == "dev" and
                          _id(argv[2], iface=True) and argv[3] == "link") or
                         (len(argv) == 5 and argv[1] == "dev" and
                          _id(argv[2], iface=True) and argv[3:] == ("station", "dump")))
        else:
            permitted = (len(argv) == 9 and argv[1:3] == ("-n", "-I") and
                         _id(argv[3], iface=True) and argv[4:6] == ("-c", "3") and
                         argv[6:8] == ("-W", "1") and
                         _private_ipv4(argv[8]))
        if not permitted:
            raise ValueError("unapproved arguments")
        # No PATH lookup from tool output, executable is resolved locally.
        exe = shutil.which(argv[0])
        if exe is None:
            raise FileNotFoundError(argv[0])
        done = subprocess.run((exe, *argv[1:]), timeout=timeout_s,
                              capture_output=True, text=True, check=False)
        # Raw iw can include BSSIDs/SSIDs; never return it through public JSON.
        return done.returncode, done.stdout[:MAX_OUTPUT]


def _private_ipv4(target: Any) -> bool:
    if not isinstance(target, str) or len(target) > 15:
        return False
    try:
        address = ipaddress.IPv4Address(target)
        return bool(address.is_private or address.is_link_local) and not (
            address.is_loopback or address.is_multicast or address.is_unspecified or
            address.is_reserved or address.is_global)
    except ipaddress.AddressValueError:
        return False


def _clean_result(status: str, *, reason: str | None = None) -> dict[str, Any]:
    return {"schema": SCHEMA, "status": status, "reason": reason,
            "readonly": True, "motor_authority": False,
            "network_change_authority": False, "physical_deployment_authority": False}


def _safe_run(runner: Any, argv: tuple[str, ...], timeout: float = 3.0) -> tuple[int, str] | None:
    try:
        code, output = runner.run(argv, timeout_s=timeout)
        if type(code) is not int or not isinstance(output, str) or len(output) > MAX_OUTPUT:
            return None
        return code, output
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired):
        return None


def list_radios(runner: Any = None) -> dict[str, Any]:
    """Discover iw-reported radio interfaces, without MAC or SSID disclosure."""
    runner = runner or ReadOnlyCommandRunner()
    result = _safe_run(runner, ("iw", "dev"))
    if result is None or result[0] != 0:
        return {**_clean_result("HOLD", reason="IW_UNAVAILABLE"), "interfaces": []}
    interfaces: list[str] = []
    for match in DEV_IF_RE.finditer(result[1]):
        if _id(match.group(1), iface=True):
            interfaces.append(match.group(1))
    unique = list(dict.fromkeys(interfaces))
    if not unique:
        return {**_clean_result("HOLD", reason="NO_WIRELESS_INTERFACES"), "interfaces": []}
    return {**_clean_result("OBSERVED"), "interfaces": unique}


def _station_counters(output: str) -> tuple[int, int] | None:
    """Only one station permitted; multi-station aggregates need separate attribution."""
    if len(STATION_RE.findall(output)) != 1:
        return None
    pk, retries = TX_PACKETS_RE.search(output), TX_RETRIES_RE.search(output)
    if not pk or not retries:
        return None
    return int(pk.group(1)), int(retries.group(1))


def _link_fields(output: str) -> dict[str, Any]:
    """Never emit raw `iw` output because it commonly contains SSID/BSSID."""
    signal = SIGNAL_RE.search(output)
    rate = BITRATE_RE.search(output)
    freq = FREQ_RE.search(output)
    rssi = float(signal.group(1)) if signal else None
    phy = float(rate.group(1)) if rate else None
    frequency = int(freq.group(1)) if freq else None
    # Bounds refuse implausible vendor output; no invented default.
    if rssi is not None and not -130 <= rssi <= 0:
        rssi = None
    if phy is not None and not 0 < phy <= 100000:
        phy = None
    if frequency is not None and not 2000 <= frequency <= 7500:
        frequency = None
    return {"rssi_dbm": rssi, "tx_phy_mbps": phy, "frequency_mhz": frequency}


def observe_radio(
    interface: str, *, runner: Any = None,
    sleeper: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.time,
    interval_s: float = 1.0,
) -> dict[str, Any]:
    """Read-only observation, with retry fraction from deltas where available.

    Retry fraction is a heuristic of tx retry attempts / (successful tx packets +
    retry attempts) across two snapshots. It is NOT raw 802.11 frame error rate
    or proof of link bandwidth. If station statistics are absent, SOMA admission
    is withheld.
    """
    if not _id(interface, iface=True) or not 0.1 <= interval_s <= 5.0:
        return _clean_result("HOLD", reason="INVALID_OBSERVER_REQUEST")
    runner = runner or ReadOnlyCommandRunner()
    available = list_radios(runner)
    if interface not in available["interfaces"]:
        return _clean_result("HOLD", reason="INTERFACE_NOT_DISCOVERED")
    link = _safe_run(runner, ("iw", "dev", interface, "link"))
    if link is None or link[0] != 0 or "Not connected." in link[1]:
        return _clean_result("HOLD", reason="LINK_UNAVAILABLE")
    fields = _link_fields(link[1])
    before = _safe_run(runner, ("iw", "dev", interface, "station", "dump"))
    try:
        sleeper(interval_s)
        observed_at = clock()
    except (ValueError, OSError, TypeError, OverflowError):
        return _clean_result("HOLD", reason="CLOCK_OR_SAMPLING_FAILURE")
    after = _safe_run(runner, ("iw", "dev", interface, "station", "dump"))
    observed_at = float(observed_at) if type(observed_at) in (int, float) else float("nan")
    if not (0 <= observed_at < float("inf")):
        return _clean_result("HOLD", reason="INVALID_OBSERVATION_TIME")
    first = _station_counters(before[1]) if before is not None and before[0] == 0 else None
    last = _station_counters(after[1]) if after is not None and after[0] == 0 else None
    retries_pct, sample_count = None, None
    if first and last:
        packet_delta, retry_delta = last[0] - first[0], last[1] - first[1]
        attempts = packet_delta + retry_delta
        if packet_delta > 0 and retry_delta >= 0 and 3 <= attempts <= 1_000_000:
            retries_pct = round((retry_delta / attempts) * 100, 3)
            sample_count = attempts
    complete = fields["rssi_dbm"] is not None and retries_pct is not None
    report = {
        **_clean_result("COMPLETE" if complete else "PARTIAL",
                        reason=None if complete else "RETRY_OR_SIGNAL_UNAVAILABLE"),
        "interface": interface, "observed_at_s": observed_at,
        "metrics": {**fields, "retry_pct": retries_pct, "sample_count": sample_count},
        "provenance": {
            "reader": "linux-iw-readonly",
            "source": "iw dev/link/station dump",
            "retry_definition": "estimated_retry_attempt_fraction",
            "traffic_generated": False,
            "tx_phy_is_not_throughput": True,
            "origin_authenticated": False,
        },
    }
    report["evidence_sha256"] = hashlib.sha256(canonical_json(report)).hexdigest()
    return report


def make_soma_radio_unsigned(
    report: dict[str, Any], *, site_id: str, node_id: str,
    peer_id: str, sequence: int, observation_id: str,
) -> dict[str, Any] | None:
    """Create an *unsigned* draft for independent lab signer/identity layer.

    Returns None on incomplete evidence. Never inserts fake retry data, signs
    packets, or creates an authority grant.
    """
    if (report.get("schema") != SCHEMA or report.get("status") != "COMPLETE"
        or not all(_id(x) for x in (site_id, node_id, peer_id, observation_id))
        or peer_id == node_id or type(sequence) is not int or not 1 <= sequence < 2**53):
        return None
    m = report.get("metrics", {})
    if type(m.get("rssi_dbm")) not in (float, int) or type(m.get("retry_pct")) not in (float, int):
        return None
    samples = m.get("sample_count")
    if type(samples) is not int or samples < 1:
        return None
    ts = report.get("observed_at_s")
    if type(ts) not in (float, int) or not 0 <= ts < float("inf"):
        return None
    # The source report is observational, not cryptographically authenticated.
    return {
        "contract": CONTRACT, "site_id": site_id, "node_id": node_id,
        "observation_id": observation_id, "organ": "sense.radio",
        "observed_at_s": ts, "sequence": sequence,
        "measurement": {"peer_id": peer_id, "rssi_dbm": m["rssi_dbm"],
                        "retry_pct": m["retry_pct"], "sample_count": samples},
        "authority": dict(AUTHORITY),
    }


def observe_ping(
    target: str, interface: str, *, approved: bool,
    runner: Any = None,
) -> dict[str, Any]:
    """Optional operator-approved packet probe; no background network activity."""
    if not approved:
        return _clean_result("HOLD", reason="OPERATOR_PROBE_APPROVAL_REQUIRED")
    if not _id(interface, iface=True) or not _private_ipv4(target):
        return _clean_result("HOLD", reason="INVALID_OR_NONPRIVATE_TARGET")
    runner = runner or ReadOnlyCommandRunner()
    discovery = list_radios(runner)
    if interface not in discovery["interfaces"]:
        return _clean_result("HOLD", reason="INTERFACE_NOT_DISCOVERED")
    result = _safe_run(runner, ("ping", "-n", "-I", interface, "-c", "3", "-W", "1", target), 6)
    if result is None or result[0] not in (0, 1):
        return _clean_result("HOLD", reason="PROBE_UNAVAILABLE")
    stats = PING_STATS_RE.search(result[1])
    rtt = PING_RTT_RE.search(result[1])
    if not stats or not rtt:
        return _clean_result("HOLD", reason="INSUFFICIENT_PROBE_REPLY")
    sent, received, loss = int(stats.group(1)), int(stats.group(2)), float(stats.group(3))
    avg = float(rtt.group(1))
    if not (sent == 3 and 0 < received <= sent and
            0 <= loss <= 100 and 0 <= avg <= 60000 and
            abs(loss - 100 * (sent - received) / sent) < 0.2):
        return _clean_result("HOLD", reason="INCONSISTENT_PROBE_DATA")
    report = {**_clean_result("OBSERVED_ADVISORY_ONLY"), "interface": interface,
              "target": target, "metrics": {"probe_rtt_avg_ms": avg,
                    "probe_packet_loss_pct": loss, "sent": sent, "received": received,
                    "observed_mbps": None},
              "provenance": {"source": "operator-approved-icmp", "traffic_generated": True,
                             "measured_throughput": False, "path_proven": False}}
    report["evidence_sha256"] = hashlib.sha256(canonical_json(report)).hexdigest()
    return report
