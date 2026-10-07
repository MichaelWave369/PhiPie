from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from .model import SensorSnapshot, SyntheticSensorAdapter


class SensorAdapter(Protocol):
    """Read-only sensor boundary for a physical host runtime."""

    def read(self) -> SensorSnapshot:
        ...


class ActuatorAdapter(Protocol):
    """Write-only actuator boundary.

    Implementations receive only actions that already passed the controller's
    deterministic authority checks.
    """

    def execute(self, capability: str, value: Any) -> Any:
        ...


@dataclass
class ScenarioSensorAdapter:
    """Deterministic scenario source used by tests and demos."""

    scenario: str = "healthy"

    def read(self) -> SensorSnapshot:
        return SyntheticSensorAdapter.snapshot(self.scenario)


@dataclass
class SequenceSensorAdapter:
    """Finite deterministic sequence of snapshots."""

    snapshots: list[SensorSnapshot]
    index: int = 0

    def read(self) -> SensorSnapshot:
        if not self.snapshots:
            raise RuntimeError("sensor sequence is empty")
        if self.index >= len(self.snapshots):
            return self.snapshots[-1]
        snapshot = self.snapshots[self.index]
        self.index += 1
        return snapshot


class NullActuatorAdapter:
    """Default actuator boundary: nothing can physically execute."""

    def execute(self, capability: str, value: Any) -> Any:
        raise RuntimeError(
            f"no physical actuator adapter installed for capability {capability!r}"
        )


@dataclass
class RecordingActuatorAdapter:
    """Simulator-only sink that records executions without touching hardware."""

    fail_capabilities: set[str] = field(default_factory=set)
    calls: list[dict[str, Any]] = field(default_factory=list)

    def execute(self, capability: str, value: Any) -> dict[str, Any]:
        if capability in self.fail_capabilities:
            raise RuntimeError(f"synthetic actuator failure: {capability}")
        record = {"capability": capability, "value": value}
        self.calls.append(record)
        return record
