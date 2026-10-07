"""Experimental Phi Physical Host simulator.

This package is intentionally non-qualifying. It provides a deterministic,
stdlib-only harness for exercising the proposed physical-host contract before
real GPIO, batteries, motors, relays, or other physical actuators are involved.
"""

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

__all__ = [
    "ActionDecision",
    "HostState",
    "PhysicalHostController",
    "SafetyLimits",
    "SensorSnapshot",
    "SyntheticSensorAdapter",
    "default_manifest",
    "validate_manifest",
]
