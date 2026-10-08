"""ΦTrail × SOMA v0.1: OFFLINE read-only admission of typed sensor evidence.

Prototype trust: preprovisioned HMAC key, scoped to exact site/node/key id, and
an in-memory replay ledger. NOT secure transport, durable anti-replay, verified
physical sensors, attested hardware, permission to observe people, or authority
for tools/motors/router changes. Future transport must provide both authenticated
peer identity and persistent replay continuity.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import hmac
import json
import math
import re
from threading import Lock
from typing import Any, Mapping

CONTRACT = "phipie-trail-soma-observation/v0.1"
RECEIPT_CONTRACT = "phipie-trail-soma-observation-receipt/v0.1"
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
AUTHORITY = {
    "grantsAuthority": False,
    "actionAuthorized": False,
    "mayInvokeTools": False,
    "mayIssueHardwareCommands": False,
    "requiresIndependentToolAuthorization": True,
    "safetyPlaneUnaffected": True,
}
ORGANS = {
    "sense.radio": {"peer_id", "rssi_dbm", "retry_pct", "sample_count"},
    "sense.network": {"parent_id", "child_id", "latency_ms", "loss_pct", "observed_mbps", "sample_count"},
    "sense.power": {"battery_pct", "supply_mv", "cpu_temp_c"},
    "sense.environment": {"temperature_c", "relative_humidity_pct"},
    "sense.location": {"zone_id", "confidence"},
    "eyes.rover": {"frame_sha256", "media_type", "width_px", "height_px", "capture_scope"},
}
# Entire payload is deliberately schema-allowlisted: no raw media, coordinates,
# SSIDs, MACs, credentials, voice transcripts, or arbitrary nested data.
NUMERIC_RANGES = {
    "rssi_dbm": (-130, 0),
    "retry_pct": (0, 100),
    "latency_ms": (0, 60000),
    "loss_pct": (0, 100),
    "observed_mbps": (0, 100000),
    "battery_pct": (0, 100),
    "supply_mv": (0, 100000),
    "cpu_temp_c": (-50, 160),
    "temperature_c": (-100, 100),
    "relative_humidity_pct": (0, 100),
    "confidence": (0, 1),
}
INT_RANGES = {"sample_count": (1, 1_000_000), "width_px": (1, 8192), "height_px": (1, 8192)}


def canonical_json(value: Any) -> bytes:
    """Canonical for this Python-only v0.1 seam, not an IETF JCS signature."""
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _id(v: Any) -> bool:
    return isinstance(v, str) and ID_RE.fullmatch(v) is not None


def _finite(v: Any) -> bool:
    if type(v) not in (int, float):
        return False
    try:
        return math.isfinite(v)
    except (OverflowError, TypeError, ValueError):
        return False


def _safe_measurement(organ: str, measurement: Any, node_id: str) -> bool:
    if not isinstance(measurement, dict) or set(measurement) != ORGANS[organ]:
        return False
    for k, v in measurement.items():
        if k in NUMERIC_RANGES:
            lo, hi = NUMERIC_RANGES[k]
            if not _finite(v) or not lo <= v <= hi:
                return False
        elif k in INT_RANGES:
            lo, hi = INT_RANGES[k]
            if type(v) is not int or not lo <= v <= hi:
                return False
        elif k in {"peer_id", "parent_id", "child_id", "zone_id"}:
            if not _id(v):
                return False
        elif k == "frame_sha256":
            if not isinstance(v, str) or not HEX64_RE.fullmatch(v):
                return False
        elif k == "media_type":
            if v != "image/jpeg":
                return False
        elif k == "capture_scope":
            if v != "operator_once":
                return False
        else:
            return False
    if organ == "sense.network":
        return (measurement["child_id"] == node_id
                and measurement["parent_id"] != node_id)
    if organ == "sense.radio":
        return measurement["peer_id"] != node_id
    return True


@dataclass(frozen=True)
class KeyBinding:
    """In-memory lab-only preprovisioned key. Do not store keys in Git or receipts."""
    site_id: str
    node_id: str
    secret: bytes


class ReplayWindow:
    """Process-local guard. Must be replaced by durable atomic store for live links."""
    def __init__(self, max_records: int = 10000) -> None:
        self._lock = Lock()
        self._seq: dict[str, int] = {}
        self._ids: set[tuple[str, str]] = set()
        self.max_records = max_records

    def admit(self, key_id: str, sequence: int, observation_id: str) -> bool:
        with self._lock:
            ident = (key_id, observation_id)
            if sequence <= self._seq.get(key_id, 0) or ident in self._ids:
                return False
            if len(self._ids) >= self.max_records:
                return False  # conservative exhaustion rather than silent eviction
            self._seq[key_id] = sequence
            self._ids.add(ident)
            return True


class SomaIntake:
    """Admit messages into a read-only observation receipt stream.

    This object owns a replay window across calls. Callers MUST NOT instantiate
    a new intake for each message, since doing so reopens replay after restart.
    This laboratory implementation is forbidden as an unattended field verifier.
    """
    def __init__(
        self,
        keyring: Mapping[str, KeyBinding],
        *,
        replay: ReplayWindow | None = None,
        max_age_s: float = 90.0,
    ):
        self._keys = dict(keyring)
        self._replay = replay if replay is not None else ReplayWindow()
        if not _finite(max_age_s) or not 0 < max_age_s <= 3600:
            raise ValueError("invalid freshness threshold")
        self.max_age_s = max_age_s

    @staticmethod
    def _refuse(reason: str) -> dict[str, Any]:
        return {
            "status": "REFUSED", "reason": reason, "receipt": None,
            "observation": None, "authorityGranted": False,
            "hardwareCommandAllowed": False, "networkChangeAllowed": False,
        }

    def receive(self, packet: Any, *, now_s: float) -> dict[str, Any]:
        if not _finite(now_s) or now_s < 0:
            return self._refuse("INVALID_CLOCK")
        if not isinstance(packet, dict):
            return self._refuse("INVALID_PACKET")
        if set(packet) != {
            "contract", "site_id", "node_id", "observation_id",
            "organ", "observed_at_s", "sequence", "measurement",
            "authority", "signature",
        }:
            return self._refuse("PACKET_SHAPE")
        if packet["contract"] != CONTRACT:
            return self._refuse("CONTRACT_MISMATCH")
        if not all(_id(packet[k]) for k in ("site_id", "node_id", "observation_id")):
            return self._refuse("INVALID_IDENTITY")
        organ = packet["organ"]
        if not isinstance(organ, str) or organ not in ORGANS:
            return self._refuse("UNKNOWN_ORGAN")
        if packet["authority"] != AUTHORITY or not isinstance(packet["authority"], dict):
            return self._refuse("AUTHORITY_ESCALATION")
        ts, seq = packet["observed_at_s"], packet["sequence"]
        if not _finite(ts) or ts < 0 or ts > now_s or now_s - ts > self.max_age_s:
            return self._refuse("STALE_OR_INVALID_TIME")
        if type(seq) is not int or not 1 <= seq < 2**53:
            return self._refuse("INVALID_SEQUENCE")
        if not _safe_measurement(organ, packet["measurement"], packet["node_id"]):
            return self._refuse("UNSAFE_MEASUREMENT")
        sig = packet["signature"]
        if not isinstance(sig, dict) or set(sig) != {"alg", "key_id", "mac_hex"}:
            return self._refuse("INVALID_SIGNATURE_FORMAT")
        if sig["alg"] != "HMAC-SHA256" or not _id(sig["key_id"]):
            return self._refuse("INVALID_SIGNATURE_FORMAT")
        if not isinstance(sig["mac_hex"], str) or not HEX64_RE.fullmatch(sig["mac_hex"]):
            return self._refuse("INVALID_SIGNATURE_FORMAT")
        binding = self._keys.get(sig["key_id"])
        if (not isinstance(binding, KeyBinding)
            or (packet["site_id"], packet["node_id"]) != (binding.site_id, binding.node_id)
            or not isinstance(binding.secret, bytes) or len(binding.secret) < 32):
            return self._refuse("UNPROVISIONED_PEER")
        body = {k: v for k, v in packet.items() if k != "signature"}
        try:
            raw = canonical_json(body)
        except (TypeError, ValueError, OverflowError):
            return self._refuse("UNENCODABLE_PACKET")
        if len(raw) > 4096:
            return self._refuse("OVERSIZE_PACKET")
        expected = hmac.new(binding.secret, raw, "sha256").hexdigest()
        if not hmac.compare_digest(expected, sig["mac_hex"]):
            return self._refuse("MAC_MISMATCH")
        if not self._replay.admit(sig["key_id"], seq, packet["observation_id"]):
            return self._refuse("REPLAY_OR_LEDGER_EXHAUSTED")
        evidence_hash = sha256(raw).hexdigest()
        receipt = {
            "contract": RECEIPT_CONTRACT,
            "type": "ObservationReceipt",
            "site_id": packet["site_id"],
            "node_id": packet["node_id"],
            "observation_id": packet["observation_id"],
            "organ": organ,
            "observed_at_s": ts,
            "received_at_s": now_s,
            "sequence": seq,
            "evidence_sha256": evidence_hash,
            "authentication": "LAB_KEYRING_HMAC_ONLY",
            "somaRuntimeWired": False,
            "actionAuthorized": False,
            "authorityGranted": False,
            "mayInvokeTools": False,
            "mayIssueHardwareCommands": False,
            "safetyPlaneUnaffected": True,
        }
        receipt["receipt_sha256"] = sha256(canonical_json(receipt)).hexdigest()
        return {
            "status": "ACCEPTED_ADVISORY_ONLY",
            "reason": None,
            "receipt": receipt,
            "observation": {
                "site_id": packet["site_id"],
                "node_id": packet["node_id"],
                "organ": organ,
                "observed_at_s": ts,
                "measurement": dict(packet["measurement"]),
            },
            "authorityGranted": False,
            "hardwareCommandAllowed": False,
            "networkChangeAllowed": False,
        }
