"""PhiPie PR20: supervised local field launch, read-only and no active probes.

This is an operator convenience wrapper around existing #14 and #16
observers. It does NOT connect two boards, provision identities, set up
servers, transmit ICMP/TCP, alter any network settings or qualify hardware.
"""
from __future__ import annotations

import os
from pathlib import Path
import platform
import shutil
import stat
import time
from typing import Any, Callable

from .field_host import capture_host
from .linux_radio import _id, list_radios, observe_radio
from .two_node_pilot import write_private_json

PREFLIGHT_CONTRACT = "phipie-trail-field-launch-preflight/v0.1"
SESSION_CONTRACT = "phipie-trail-local-capture-session/v0.1"
ROLES = {"sender", "receiver"}
PI_TARGETS = {"RPI5_REPORTED", "CM5_REPORTED"}


def doctor(
    interface: str, *, runner: Any = None,
    which: Callable[[str], str | None] = shutil.which,
    system: str | None = None,
    host: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Passive: reads Linux system information and runs only `iw dev`.

    iperf3 and ping are *never* run by doctor or collect. Presence of an
    executable on PATH does not prove it is safe, working or authenticated.
    """
    reasons = []
    system_name = system if system is not None else platform.system()
    if not _id(interface, iface=True):
        reasons.append("INVALID_INTERFACE_ALIAS")
    host = host if host is not None else capture_host()
    if not isinstance(host, dict) or host.get("schema") != "phipie-trail-host-snapshot/v0.1":
        reasons.append("INVALID_HOST_RECORD")
        family = "UNKNOWN"
    else:
        family = host.get("platform")
    if system_name != "Linux":
        reasons.append("LINUX_REQUIRED")
    if not isinstance(family, str) or family not in PI_TARGETS:
        reasons.append("PI_FAMILY_NOT_REPORTED")
    tool_found = {}
    for tool in ("iw", "ping", "iperf3"):
        try:
            exe = which(tool)
            tool_found[tool] = bool(isinstance(exe, str) and exe)
        except (OSError, ValueError, TypeError):
            tool_found[tool] = False
    if not tool_found["iw"]:
        reasons.append("IW_TOOL_MISSING")
    radio_found = False
    if (not reasons and tool_found["iw"]):
        observed = list_radios(runner)
        radio_found = interface in observed.get("interfaces", ())
        if not radio_found:
            reasons.append("WIRELESS_INTERFACE_NOT_DISCOVERED")
    result = {
        "contract": PREFLIGHT_CONTRACT,
        "status": "READY_FOR_READONLY_CAPTURE" if not reasons else "HOLD",
        "reasons": sorted(set(reasons)),
        "reported_platform": family if isinstance(family, str) else "UNKNOWN",
        "linux_reported": system_name == "Linux",
        "requested_interface_discovered": radio_found,
        "tool_executable_found": tool_found,
        "host_snapshot_sha256": host.get("snapshot_sha256") if isinstance(host, dict) else None,
        "tool_presence_does_not_prove_working_driver": True,
        "clock_trust_established": False,
        "physical_hardware_qualified": False,
        "site_authority_verified": False,
        "operator_identity_verified": False,
        "network_traffic_generated": False,
        "network_change_authorized": False,
        "rover_motion_authorized": False,
        "remote_transport_established": False,
    }
    return result


def _safe_new_directory(root: str | Path) -> Path:
    path = Path(root)
    parent = path.parent
    if not parent.is_dir() or parent.is_symlink() or path.is_symlink() or path.exists():
        raise ValueError("new local session path required")
    # Prevent symlink surprises in any existing parent path component.
    cursor = parent
    while cursor != cursor.parent:
        if cursor.is_symlink():
            raise ValueError("symlinked parent directory")
        cursor = cursor.parent
    path.mkdir(mode=0o700, exist_ok=False)
    info = path.stat()
    if (not stat.S_ISDIR(info.st_mode)
        or (os.name == "posix" and (info.st_mode & 0o077 or info.st_uid != os.geteuid()))):
        raise PermissionError("new session directory must be owner only")
    return path


def collect_local(
    directory: str | Path, *, role: str, node_id: str,
    test_id: str, interface: str, runner: Any = None,
    which: Callable[[str], str | None] = shutil.which,
    system: str | None = None,
    host: dict[str, Any] | None = None,
    clock: Callable[[], float] = time.time,
    sleeper: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """One passive observation, then three new private files.

    A driver that cannot report retry counters may yield PARTIAL, and
    we still preserve the evidence with a HOLD-for-qualification status.
    No claim that this was a distinct, authenticated physical board.
    """
    if not isinstance(role, str) or role not in ROLES or not _id(node_id) or not _id(test_id):
        return {"status": "HOLD", "reason": "INVALID_SESSION_IDENTITY",
                "files_written": False, "physical_hardware_qualified": False}
    host = host if host is not None else capture_host()
    preflight = doctor(interface, runner=runner, which=which, system=system, host=host)
    if preflight["status"] != "READY_FOR_READONLY_CAPTURE":
        return {"status": "HOLD", "reason": "PREFLIGHT_HOLD",
                "reasons": preflight["reasons"], "files_written": False,
                "physical_hardware_qualified": False}
    radio = observe_radio(interface, runner=runner, sleeper=sleeper, clock=clock)
    status = ("LOCAL_CAPTURE_RECORDED" if radio.get("status") == "COMPLETE"
              else "PARTIAL_OR_UNAVAILABLE_RADIO")
    session = {
        "contract": SESSION_CONTRACT,
        "test_id": test_id,
        "node_role": role,
        "node_alias": node_id,
        "radio_interface_alias": interface,
        "reported_platform": host["platform"],
        "host_snapshot_sha256": host.get("snapshot_sha256"),
        "radio_report_sha256": radio.get("evidence_sha256"),
        "radio_status": radio.get("status"),
        "status": status,
        "evidence_origin": "LOCAL_LINUX_UNATTESTED",
        "network_traffic_generated": False,
        "sender_or_receiver_identity_attested": False,
        "boot_session_independently_verified": False,
        "site_permission_independently_verified": False,
        "soma_runtime_wired": False,
        "network_change_authorized": False,
        "rover_motion_authorized": False,
        "physical_hardware_qualified": False,
        "two_node_field_trial_completed": False,
    }
    path = _safe_new_directory(directory)
    write_private_json(path / "host.json", host)
    write_private_json(path / "radio.json", radio)
    write_private_json(path / "session.json", session)
    return {
        "status": status,
        "files_written": True,
        "saved_host": True,
        "saved_radio": True,
        "radio_status": radio.get("status"),
        "host_snapshot_sha256": host.get("snapshot_sha256"),
        "radio_report_sha256": radio.get("evidence_sha256"),
        "no_active_network_probe": True,
        "physical_hardware_qualified": False,
        "two_node_field_trial_completed": False,
        "network_change_authorized": False,
        "rover_motion_authorized": False,
    }
