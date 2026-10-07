"""Experimental Phi Physical Host runtime.

This package is intentionally non-qualifying. It provides deterministic,
stdlib-only contracts for exercising the proposed physical-host architecture
before real GPIO, batteries, motors, relays, or other physical actuators are
introduced.
"""

from .health_baseline import (
    BASELINE_CONTRACT,
    MetricBaseline,
    MetricDrift,
    PiHealthBaseline,
    PiHealthBaselineBuilder,
    PiHealthDriftReport,
    PiHealthObserver,
)
from .io import (
    NullActuatorAdapter,
    RecordingActuatorAdapter,
    ScenarioSensorAdapter,
    SensorAdapter,
    SequenceSensorAdapter,
)
from .model import (
    ActionDecision,
    HostState,
    PhysicalHostController,
    SafetyLimits,
    SensorSnapshot,
    SyntheticSensorAdapter,
    default_manifest,
    validate_manifest,
)
from .pi_telemetry import (
    NetworkInterfaceObservation,
    PiTelemetryObserver,
    PiTelemetrySnapshot,
    RaspberryPiTelemetryAdapter,
)
from .runtime import PhysicalHostRuntime

__all__ = [
    "ActionDecision",
    "BASELINE_CONTRACT",
    "HostState",
    "MetricBaseline",
    "MetricDrift",
    "NetworkInterfaceObservation",
    "NullActuatorAdapter",
    "PhysicalHostController",
    "PhysicalHostRuntime",
    "PiHealthBaseline",
    "PiHealthBaselineBuilder",
    "PiHealthDriftReport",
    "PiHealthObserver",
    "PiTelemetryObserver",
    "PiTelemetrySnapshot",
    "RaspberryPiTelemetryAdapter",
    "RecordingActuatorAdapter",
    "SafetyLimits",
    "ScenarioSensorAdapter",
    "SensorAdapter",
    "SensorSnapshot",
    "SequenceSensorAdapter",
    "SyntheticSensorAdapter",
    "default_manifest",
    "validate_manifest",
]
