from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable


class HostState(str, Enum):
    BOOT_SELFTEST = "BOOT_SELFTEST"
    SAFE_IDLE = "SAFE_IDLE"
    READY = "READY"
    ACTIVE = "ACTIVE"
    DERATE = "DERATE"
    PROTECT = "PROTECT"
    FAULT_LATCH = "FAULT_LATCH"
    RECOVERY = "RECOVERY"
    MAINTENANCE = "MAINTENANCE"


class ActionDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    CLAMP = "clamp"
    REVIEW = "review"


@dataclass(frozen=True)
class SafetyLimits:
    rail_min_v: float = 4.75
    rail_max_v: float = 5.25
    current_derate_a: float = 3.5
    current_protect_a: float = 4.5
    board_temp_derate_c: float = 72.0
    board_temp_protect_c: float = 82.0
    humidity_warn_pct: float = 90.0


@dataclass(frozen=True)
class SensorSnapshot:
    rail_v: float = 5.0
    current_a: float = 1.0
    board_temp_c: float = 45.0
    ambient_temp_c: float = 24.0
    humidity_pct: float = 45.0
    airflow_ok: bool = True
    leak: bool = False
    estop: bool = False
    sensor_fresh: bool = True
    network_ok: bool = True
    model_ok: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_manifest(host_id: str = "phipie-sim-001") -> dict[str, Any]:
    return {
        "contract": "phi-physical-host/v0.1",
        "host_id": host_id,
        "platform": "synthetic",
        "profile": "lab-node",
        "planes": {
            "identity": "present",
            "power": "observed",
            "thermal": "observed",
            "environment": "observed",
            "safety": "deterministic-local",
            "service": "declared",
            "action": "bounded",
            "receipts": "local-first",
        },
        "compute": {"serviceable": True},
        "battery": {"present": False, "serviceable": True},
        "network_loss_safe": True,
        "cloud_required_for_safety": False,
        "authority": {
            "hazardous_action_requires_plane_a": True,
            "phibot_direct_physical_authority": False,
        },
    }


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if manifest.get("contract") != "phi-physical-host/v0.1":
        errors.append("contract must be phi-physical-host/v0.1")
    if not manifest.get("host_id"):
        errors.append("host_id is required")
    if manifest.get("cloud_required_for_safety") is not False:
        errors.append("cloud_required_for_safety must be false for the simulator")
    if manifest.get("network_loss_safe") is not True:
        errors.append("network_loss_safe must be true for the simulator")

    authority = manifest.get("authority") or {}
    if authority.get("hazardous_action_requires_plane_a") is not True:
        errors.append("hazardous_action_requires_plane_a must be true")
    if authority.get("phibot_direct_physical_authority") is not False:
        errors.append("phibot_direct_physical_authority must be false")

    planes = manifest.get("planes") or {}
    required_planes = {
        "identity",
        "power",
        "thermal",
        "environment",
        "safety",
        "service",
        "action",
        "receipts",
    }
    missing = sorted(required_planes.difference(planes))
    if missing:
        errors.append("missing planes: " + ", ".join(missing))

    return errors


class ReceiptChain:
    def __init__(self, host_id: str, clock: Callable[[], datetime]) -> None:
        self.host_id = host_id
        self.clock = clock
        self.receipts: list[dict[str, Any]] = []
        self._head = "0" * 64

    @property
    def head(self) -> str:
        return self._head

    @staticmethod
    def _canonical(payload: dict[str, Any]) -> bytes:
        return json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")

    def append(
        self,
        *,
        source_plane: str,
        event_kind: str,
        state_before: HostState,
        state_after: HostState,
        inputs: dict[str, Any],
        decision: str,
        action: dict[str, Any] | None,
        reason: str,
        operator_action: str | None = None,
        evidence_refs: list[str] | None = None,
        share_level: str = "local",
    ) -> dict[str, Any]:
        timestamp = self.clock().astimezone(timezone.utc).isoformat()
        body: dict[str, Any] = {
            "id": f"receipt-{len(self.receipts) + 1:06d}",
            "timestamp": timestamp,
            "host_id": self.host_id,
            "source_plane": source_plane,
            "event_kind": event_kind,
            "state_before": state_before.value,
            "state_after": state_after.value,
            "inputs": inputs,
            "decision": decision,
            "action": action,
            "reason": reason,
            "operator_action": operator_action,
            "software": {"component": "physical-host-sim", "contract": "v0.1"},
            "evidence_refs": evidence_refs or [],
            "previous_hash": self._head,
            "share_level": share_level,
        }
        digest = hashlib.sha256(self._canonical(body)).hexdigest()
        receipt = {**body, "current_hash": digest}
        self.receipts.append(receipt)
        self._head = digest
        return receipt

    def verify(self) -> bool:
        previous = "0" * 64
        for receipt in self.receipts:
            body = dict(receipt)
            current_hash = body.pop("current_hash", None)
            if body.get("previous_hash") != previous:
                return False
            expected = hashlib.sha256(self._canonical(body)).hexdigest()
            if expected != current_hash:
                return False
            previous = current_hash
        return previous == self._head


class PhysicalHostController:
    """Deterministic Plane A simulator with bounded action requests.

    This is deliberately small. It proves software contracts and refusal
    behavior only. It does not qualify real sensors, actuators, GPIO, power
    electronics, batteries, enclosures, or safety hardware.
    """

    def __init__(
        self,
        manifest: dict[str, Any] | None = None,
        limits: SafetyLimits | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.manifest = manifest or default_manifest()
        errors = validate_manifest(self.manifest)
        if errors:
            raise ValueError("; ".join(errors))

        self.limits = limits or SafetyLimits()
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.state = HostState.BOOT_SELFTEST
        self.last_snapshot: SensorSnapshot | None = None
        self.receipts = ReceiptChain(self.manifest["host_id"], self.clock)

    def _classify(self, snap: SensorSnapshot) -> tuple[HostState | None, str]:
        l = self.limits

        if snap.estop:
            return HostState.FAULT_LATCH, "emergency stop asserted"
        if snap.leak:
            return HostState.FAULT_LATCH, "leak/moisture fault"
        if not snap.sensor_fresh:
            return HostState.PROTECT, "safety-critical sensor data stale"
        if snap.rail_v < l.rail_min_v or snap.rail_v > l.rail_max_v:
            return HostState.PROTECT, "power rail outside hard envelope"
        if snap.current_a >= l.current_protect_a:
            return HostState.PROTECT, "current above protect threshold"
        if snap.board_temp_c >= l.board_temp_protect_c:
            return HostState.PROTECT, "board temperature above protect threshold"
        if snap.current_a >= l.current_derate_a:
            return HostState.DERATE, "current above derate threshold"
        if snap.board_temp_c >= l.board_temp_derate_c:
            return HostState.DERATE, "board temperature above derate threshold"
        if snap.humidity_pct >= l.humidity_warn_pct and not snap.airflow_ok:
            return HostState.DERATE, "high humidity with lost airflow"
        return None, "snapshot inside declared envelope"

    def boot(self, snap: SensorSnapshot) -> dict[str, Any]:
        before = self.state
        target, reason = self._classify(snap)
        self.last_snapshot = snap
        self.state = target or HostState.SAFE_IDLE
        return self.receipts.append(
            source_plane="safety",
            event_kind="boot_selftest",
            state_before=before,
            state_after=self.state,
            inputs=snap.to_dict(),
            decision="protect" if target else "pass",
            action={"local_safe_state": self.state.value},
            reason=reason,
        )

    def arm(self) -> dict[str, Any]:
        before = self.state
        if self.state not in {HostState.SAFE_IDLE, HostState.RECOVERY}:
            decision = "deny"
            reason = f"cannot arm from {self.state.value}"
            after = self.state
        elif self.last_snapshot is None:
            decision = "deny"
            reason = "no sensor snapshot"
            after = self.state
        else:
            target, reason = self._classify(self.last_snapshot)
            if target:
                decision = "deny"
                after = target
                self.state = target
            else:
                decision = "allow"
                reason = "explicit arm after safe snapshot"
                self.state = HostState.READY
                after = self.state

        return self.receipts.append(
            source_plane="safety",
            event_kind="arm_request",
            state_before=before,
            state_after=after,
            inputs=self.last_snapshot.to_dict() if self.last_snapshot else {},
            decision=decision,
            action={"armed": decision == "allow"},
            reason=reason,
        )

    def ingest(self, snap: SensorSnapshot) -> dict[str, Any]:
        before = self.state
        self.last_snapshot = snap
        target, reason = self._classify(snap)

        if self.state == HostState.FAULT_LATCH:
            after = self.state
            decision = "latched"
            reason = "fault latch requires explicit operator reset"
        elif target is not None:
            self.state = target
            after = self.state
            decision = "protect" if target in {HostState.PROTECT, HostState.FAULT_LATCH} else "derate"
        elif self.state in {HostState.DERATE, HostState.PROTECT}:
            self.state = HostState.RECOVERY
            after = self.state
            decision = "recover"
            reason = "snapshot returned to safe envelope; re-arm required"
        else:
            after = self.state
            decision = "observe"

        return self.receipts.append(
            source_plane="environment",
            event_kind="sensor_snapshot",
            state_before=before,
            state_after=after,
            inputs=snap.to_dict(),
            decision=decision,
            action=None,
            reason=reason,
        )

    def reset_fault(self, *, operator_confirmed: bool) -> dict[str, Any]:
        before = self.state

        if self.state != HostState.FAULT_LATCH:
            decision = "deny"
            reason = "no latched fault exists"
        elif not operator_confirmed:
            decision = "deny"
            reason = "operator confirmation required"
        elif self.last_snapshot is None:
            decision = "deny"
            reason = "no sensor snapshot"
        else:
            target, safety_reason = self._classify(self.last_snapshot)
            if target is not None:
                decision = "deny"
                reason = f"fault condition remains: {safety_reason}"
            else:
                decision = "allow"
                reason = "operator reset accepted after safe snapshot"
                self.state = HostState.RECOVERY

        return self.receipts.append(
            source_plane="safety",
            event_kind="fault_reset",
            state_before=before,
            state_after=self.state,
            inputs=self.last_snapshot.to_dict() if self.last_snapshot else {},
            decision=decision,
            action={"reset": decision == "allow"},
            reason=reason,
            operator_action="confirmed" if operator_confirmed else "not_confirmed",
        )

    def request_action(
        self,
        *,
        capability: str,
        requested_value: Any,
        requested_by: str,
        authority_granted: bool = False,
    ) -> dict[str, Any]:
        before = self.state
        allowlist = {"fan.set", "status.led", "load.enable"}

        decision = ActionDecision.DENY
        executed_value: Any = None
        reason = "capability is not allowlisted"

        if capability in allowlist:
            if requested_by == "phibot" and not authority_granted:
                decision = ActionDecision.REVIEW
                reason = "PhiBot request has no direct physical authority"
            elif capability == "status.led":
                decision = ActionDecision.ALLOW
                executed_value = str(requested_value)
                reason = "status indicator is within simulator allowlist"
            elif capability == "fan.set":
                try:
                    raw = float(requested_value)
                except (TypeError, ValueError):
                    decision = ActionDecision.DENY
                    reason = "fan.set requires numeric percentage"
                else:
                    bounded = max(0.0, min(100.0, raw))
                    executed_value = bounded
                    decision = (
                        ActionDecision.ALLOW
                        if bounded == raw
                        else ActionDecision.CLAMP
                    )
                    reason = "fan request bounded to 0..100 percent"
            elif capability == "load.enable":
                if bool(requested_value) and self.state not in {
                    HostState.READY,
                    HostState.ACTIVE,
                }:
                    decision = ActionDecision.DENY
                    reason = f"load cannot enable from {self.state.value}"
                else:
                    decision = ActionDecision.ALLOW
                    executed_value = bool(requested_value)
                    reason = "load request is inside current safety state"
                    if executed_value and self.state == HostState.READY:
                        self.state = HostState.ACTIVE
                    elif not executed_value and self.state == HostState.ACTIVE:
                        self.state = HostState.READY

        action = {
            "capability": capability,
            "requested_value": requested_value,
            "requested_by": requested_by,
            "authority_granted": authority_granted,
            "authority_decision": decision.value,
            "executed_value": executed_value,
        }

        return self.receipts.append(
            source_plane="action",
            event_kind="action_request",
            state_before=before,
            state_after=self.state,
            inputs=self.last_snapshot.to_dict() if self.last_snapshot else {},
            decision=decision.value,
            action=action,
            reason=reason,
        )


class SyntheticSensorAdapter:
    """Named, deterministic snapshots for tests and demos."""

    SCENARIOS: dict[str, SensorSnapshot] = {
        "healthy": SensorSnapshot(),
        "thermal_derate": SensorSnapshot(board_temp_c=75.0),
        "thermal_protect": SensorSnapshot(board_temp_c=86.0),
        "overcurrent": SensorSnapshot(current_a=4.8),
        "leak": SensorSnapshot(leak=True),
        "stale_sensor": SensorSnapshot(sensor_fresh=False),
        "network_loss": SensorSnapshot(network_ok=False, model_ok=False),
        "humid_no_airflow": SensorSnapshot(humidity_pct=94.0, airflow_ok=False),
    }

    @classmethod
    def snapshot(cls, scenario: str) -> SensorSnapshot:
        try:
            return cls.SCENARIOS[scenario]
        except KeyError as exc:
            known = ", ".join(sorted(cls.SCENARIOS))
            raise KeyError(f"unknown scenario {scenario!r}; choose from: {known}") from exc
