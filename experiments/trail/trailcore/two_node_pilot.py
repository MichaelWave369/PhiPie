"""Two-node ΦTrail pilot: manual signed file handoff, offline verification only.

No sockets, SSH, AP changes, automatic probing, router configuration, or rover
commands. HMAC is a shared lab secret: neither physical-device attestation nor
trusted measurement provenance. The receiver's SQLite replay ledger survives
normal process restarts; deletion or rollback of its disk remains unprotected.
"""
from __future__ import annotations
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import stat
import time
from hashlib import sha256
from typing import Any

from .durable_replay import DurableReplayWindow
from .linux_radio import make_soma_radio_unsigned, observe_radio
from .soma_observation import KeyBinding, SomaIntake, canonical_json

HEX_KEY = re.compile(r"^[0-9a-f]{64}$")
MAX_INPUT_BYTES = 8192


def create_lab_key(path: str | Path) -> None:
    """Operator-triggered provisioning into new owner-only file; no overwrite."""
    p = Path(path)
    if not p.parent.is_dir() or p.is_symlink():
        raise ValueError("key destination parent missing or symlink")
    fd = os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="ascii") as f:
            f.write(secrets.token_hex(32) + "\n")
            f.flush()
            os.fsync(f.fileno())
    except BaseException:
        raise  # incomplete key file remains as a visible provisioning failure


def read_lab_key(path: str | Path) -> bytes:
    p = Path(path)
    if not p.is_file() or p.is_symlink():
        raise ValueError("key missing or symlink")
    if os.name == "posix" and p.stat().st_mode & 0o077:
        raise PermissionError("key file permissions must be owner-only (0600)")
    if p.stat().st_size > 128:
        raise ValueError("key file oversized")
    key = p.read_text("ascii").strip()
    if not HEX_KEY.fullmatch(key):
        raise ValueError("key file must contain exactly 32 random bytes in hex")
    return bytes.fromhex(key)


def _strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in pairs:
        if k in out:
            raise ValueError("duplicate object key")
        out[k] = v
    return out


def _refuse_constant(v: str) -> None:
    raise ValueError("nonfinite JSON constant")


def read_packet_file(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file() or p.is_symlink() or p.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("packet input missing, symlink, or oversized")
    if os.name == "posix" and p.stat().st_mode & 0o077:
        raise PermissionError("private signed packet must be owner-only (0600)")
    data = json.loads(p.read_text("utf-8"), object_pairs_hook=_strict_pairs,
                      parse_constant=_refuse_constant)
    if not isinstance(data, dict):
        raise ValueError("packet root must be an object")
    return data


def write_private_json(path: str | Path, value: dict[str, Any]) -> None:
    """No stdout dump of identifiers. No clobber, symlink-follow or secret logging."""
    p = Path(path)
    if not p.parent.is_dir() or p.is_symlink():
        raise ValueError("output parent missing or symlink")
    raw = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False,
                     allow_nan=False).encode("utf-8") + b"\n"
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("output too large")
    fd = os.open(p, os.O_WRONLY | os.O_EXCL | os.O_CREAT, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())


def sign_complete_radio_report(report: dict[str, Any], *,
                               site_id: str, node_id: str, peer_id: str,
                               key_id: str, secret: bytes, sequence: int,
                               observation_id: str) -> dict[str, Any] | None:
    """Only a COMPLETE observer can emit a signed candidate for transfer.

    Caller-provided site/node/peer aliases are NOT independently verified.
    This must not become an automatic trust anchor or claims of RF coverage.
    """
    if not isinstance(key_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,63}", key_id):
        return None
    if not isinstance(secret, bytes) or len(secret) != 32:
        return None
    unsigned = make_soma_radio_unsigned(
        report, site_id=site_id, node_id=node_id, peer_id=peer_id,
        sequence=sequence, observation_id=observation_id,
    )
    if unsigned is None:
        return None
    mac = hmac.new(secret, canonical_json(unsigned), sha256).hexdigest()
    return {**unsigned, "signature": {"alg": "HMAC-SHA256", "key_id": key_id, "mac_hex": mac}}


def collect_signed_radio(*, interface: str, site_id: str, node_id: str,
                         peer_id: str, key_id: str, key_file: str | Path,
                         sequence: int, runner: Any = None,
                         sleeper: Any = time.sleep, clock: Any = time.time,
                         observation_id: str | None = None) -> dict[str, Any] | None:
    """One operator request: read radio locally and produce a bounded packet."""
    secret = read_lab_key(key_file)
    report = observe_radio(interface, runner=runner, sleeper=sleeper, clock=clock)
    if report.get("status") != "COMPLETE":
        return None
    return sign_complete_radio_report(
        report, site_id=site_id, node_id=node_id, peer_id=peer_id,
        key_id=key_id, secret=secret, sequence=sequence,
        observation_id=observation_id or ("radio-" + secrets.token_hex(12)),
    )


def receive_signed_radio(packet: Any, *, site_id: str, node_id: str,
                         key_id: str, key_file: str | Path,
                         replay_db: str | Path, now_s: float) -> dict[str, Any]:
    """Consume exactly one HMAC-checked, replay-refused packet.

    Returns receipt only: never a tool executor, raw radio output or actuator.
    """
    secret = read_lab_key(key_file)
    replay = DurableReplayWindow(replay_db)
    receiver = SomaIntake({key_id: KeyBinding(site_id, node_id, secret)}, replay=replay)
    admitted = receiver.receive(packet, now_s=now_s)
    if admitted["status"] != "ACCEPTED_ADVISORY_ONLY":
        return {
            "status": "HOLD",
            "reason": admitted["reason"],
            "receipt": None,
            "networkChangeAllowed": False,
            "roverMotionAllowed": False,
        }
    if admitted["observation"]["organ"] != "sense.radio":
        # Non-radio HMAC-valid observations must never be treated as radio data.
        return {
            "status": "HOLD", "reason": "NOT_RADIO_ORGAN", "receipt": None,
            "networkChangeAllowed": False, "roverMotionAllowed": False,
        }
    return {
        "status": "ACCEPTED_ADVISORY_ONLY",
        "reason": None,
        "receipt": admitted["receipt"],
        "networkChangeAllowed": False,
        "roverMotionAllowed": False,
        "fieldIdentityAttested": False,
        "radioMeasurementAttested": False,
        "networkTransportEstablished": False,
        "replayStore": "LOCAL_SQLITE_V0.1",
    }
