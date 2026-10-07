from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone

from runtime.physical_host import HostState, PhysicalHostController
from runtime.physical_host.health_baseline import (
    BASELINE_CONTRACT,
    PiHealthBaseline,
    PiHealthBaselineBuilder,
    PiHealthObserver,
)
from runtime.physical_host.pi_telemetry import (
    NetworkInterfaceObservation,
    PiTelemetrySnapshot,
)


FIXED_TIME = datetime(2026, 10, 7, 13, 30, tzinfo=timezone.utc)


def fixed_clock() -> datetime:
    return FIXED_TIME


def snapshot(
    *,
    temp: float | None = 50.0,
    load: float | None = 0.5,
    memory_available: int | None = 6000,
    memory_total: int | None = 8000,
    voltage: float | None = 0.72,
    carrier_up: int = 1,
    flags: list[str] | None = None,
    board_hash: str | None = "board-a",
    machine_hash: str | None = "machine-a",
) -> PiTelemetrySnapshot:
    interfaces = [
        NetworkInterfaceObservation(
            name=f"eth{index}",
            operstate="up",
            carrier=True,
        )
        for index in range(carrier_up)
    ]
    return PiTelemetrySnapshot(
        raspberry_pi_detected=True,
        model="Raspberry Pi 5 Model B Rev 1.0",
        compatible=["raspberrypi,5-model-b", "brcm,bcm2712"],
        board_serial_sha256=board_hash,
        machine_id_sha256=machine_hash,
        cpu_temp_c=temp,
        uptime_s=1000.0,
        load_1m=load,
        load_5m=load,
        load_15m=load,
        memory_total_kib=memory_total,
        memory_available_kib=memory_available,
        throttled_raw="0x0" if not flags else "0x1",
        throttled_flags=flags or [],
        core_voltage_v=voltage,
        network_interfaces=interfaces,
        provenance={},
        warnings=[],
    )


def build_baseline() -> PiHealthBaseline:
    builder = PiHealthBaselineBuilder()
    for temp in (49.0, 50.0, 50.0, 51.0, 50.0):
        builder.add(snapshot(temp=temp))
    return builder.finalize()


class StaticTelemetry:
    def __init__(self, value: PiTelemetrySnapshot) -> None:
        self.value = value

    def read(self) -> PiTelemetrySnapshot:
        return self.value


class PiHealthBaselineTests(unittest.TestCase):
    def test_requires_minimum_samples(self) -> None:
        builder = PiHealthBaselineBuilder()
        for _ in range(4):
            builder.add(snapshot())
        with self.assertRaises(ValueError):
            builder.finalize()

    def test_baseline_is_versioned_and_identity_bound(self) -> None:
        baseline = build_baseline()
        self.assertEqual(BASELINE_CONTRACT, baseline.contract)
        self.assertEqual(5, baseline.sample_count)
        self.assertEqual("board-a", baseline.identity["board_serial_sha256"])
        self.assertEqual("machine-a", baseline.identity["machine_id_sha256"])

    def test_refuses_to_mix_different_hosts(self) -> None:
        builder = PiHealthBaselineBuilder()
        builder.add(snapshot(board_hash="board-a"))
        with self.assertRaises(ValueError):
            builder.add(snapshot(board_hash="board-b"))

    def test_normal_observation_is_stable(self) -> None:
        report = build_baseline().evaluate(snapshot(temp=50.5, load=0.55))
        self.assertEqual("stable", report.classification)
        self.assertTrue(report.identity_match)
        self.assertEqual("none", report.authority_effect)

    def test_large_temperature_drift_is_notable_but_not_authority(self) -> None:
        report = build_baseline().evaluate(snapshot(temp=60.0))
        self.assertEqual("notable", report.classification)
        self.assertEqual(
            "notable",
            report.metrics["cpu_temp_c"].classification,
        )
        self.assertGreaterEqual(
            report.metrics["cpu_temp_c"].magnitude_score,
            6.0,
        )
        self.assertEqual("none", report.authority_effect)

    def test_new_throttle_flag_is_notable(self) -> None:
        report = build_baseline().evaluate(
            snapshot(flags=["under_voltage_now"])
        )
        self.assertEqual("notable", report.classification)
        self.assertEqual(
            ["under_voltage_now"],
            report.new_throttled_flags,
        )

    def test_identity_mismatch_refuses_drift_scoring(self) -> None:
        report = build_baseline().evaluate(
            snapshot(board_hash="board-b", machine_hash="machine-b")
        )
        self.assertEqual("identity_mismatch", report.classification)
        self.assertFalse(report.identity_match)
        self.assertEqual({}, report.metrics)

    def test_missing_metric_is_reported_not_fabricated(self) -> None:
        report = build_baseline().evaluate(snapshot(temp=None))
        self.assertNotIn("cpu_temp_c", report.metrics)
        self.assertIn(
            "cpu_temp_c unavailable for drift comparison",
            report.warnings,
        )

    def test_round_trip_preserves_baseline(self) -> None:
        original = build_baseline()
        encoded = json.dumps(original.to_dict(), sort_keys=True)
        restored = PiHealthBaseline.from_dict(json.loads(encoded))
        self.assertEqual(original.to_dict(), restored.to_dict())

    def test_observer_writes_diagnostic_receipt_without_changing_state(self) -> None:
        controller = PhysicalHostController(clock=fixed_clock)
        baseline = build_baseline()
        observer = PiHealthObserver(
            controller,
            StaticTelemetry(snapshot(temp=65.0)),
            baseline,
        )

        before = controller.state
        receipt = observer.observe()

        self.assertEqual(HostState.BOOT_SELFTEST, before)
        self.assertEqual(before, controller.state)
        self.assertEqual("observe", receipt["decision"])
        self.assertEqual("rpi_health_drift", receipt["event_kind"])
        self.assertEqual(
            "notable",
            receipt["diagnostic_report"]["classification"],
        )
        self.assertIsNone(receipt["action"])
        self.assertTrue(controller.receipts.verify())

    def test_baseline_and_observer_expose_no_execute_surface(self) -> None:
        baseline = build_baseline()
        observer = PiHealthObserver(
            PhysicalHostController(clock=fixed_clock),
            StaticTelemetry(snapshot()),
            baseline,
        )
        self.assertFalse(hasattr(baseline, "execute"))
        self.assertFalse(hasattr(observer, "execute"))


if __name__ == "__main__":
    unittest.main()
