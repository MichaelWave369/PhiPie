from __future__ import annotations

import hashlib
import json
import unittest
from datetime import datetime, timezone

from runtime.physical_host import HostState, PhysicalHostController
from runtime.physical_host.pi_telemetry import (
    PiTelemetryObserver,
    RaspberryPiTelemetryAdapter,
)


FIXED_TIME = datetime(2026, 10, 7, 13, 20, tzinfo=timezone.utc)


def fixed_clock() -> datetime:
    return FIXED_TIME


class FakeHost:
    def __init__(self) -> None:
        self.files = {
            "/proc/device-tree/model": "Raspberry Pi 5 Model B Rev 1.0\x00",
            "/proc/device-tree/compatible": "raspberrypi,5-model-b\x00brcm,bcm2712\x00",
            "/proc/device-tree/serial-number": "10000000cafefeed\x00",
            "/etc/machine-id": "0123456789abcdef0123456789abcdef\n",
            "/sys/class/thermal/thermal_zone0/temp": "61250\n",
            "/proc/uptime": "12345.67 999.00\n",
            "/proc/loadavg": "0.25 0.50 0.75 1/100 123\n",
            "/proc/meminfo": (
                "MemTotal:        8178892 kB\n"
                "MemFree:         1000000 kB\n"
                "MemAvailable:    6123456 kB\n"
            ),
            "/sys/class/net/eth0/operstate": "up\n",
            "/sys/class/net/eth0/carrier": "1\n",
            "/sys/class/net/wlan0/operstate": "down\n",
            "/sys/class/net/wlan0/carrier": "0\n",
        }
        self.commands = {
            ("vcgencmd", "get_throttled"): "throttled=0x50005\n",
            ("vcgencmd", "measure_volts", "core"): "volt=0.7200V\n",
        }
        self.command_calls: list[tuple[str, ...]] = []

    def read_text(self, path: str) -> str | None:
        return self.files.get(path)

    def listdir(self, path: str) -> list[str]:
        if path == "/sys/class/net":
            return ["eth0", "lo", "wlan0"]
        return []

    def run_command(self, argv: list[str]) -> str | None:
        key = tuple(argv)
        self.command_calls.append(key)
        return self.commands.get(key)


class PiTelemetryTests(unittest.TestCase):
    def adapter(self, host: FakeHost) -> RaspberryPiTelemetryAdapter:
        return RaspberryPiTelemetryAdapter(
            read_text=host.read_text,
            listdir=host.listdir,
            run_command=host.run_command,
        )

    def test_reads_pi_identity_and_hashes_serials(self) -> None:
        host = FakeHost()
        snap = self.adapter(host).read()

        self.assertTrue(snap.raspberry_pi_detected)
        self.assertEqual("Raspberry Pi 5 Model B Rev 1.0", snap.model)
        self.assertEqual(
            hashlib.sha256(b"10000000cafefeed").hexdigest(),
            snap.board_serial_sha256,
        )
        self.assertEqual(
            hashlib.sha256(
                b"0123456789abcdef0123456789abcdef"
            ).hexdigest(),
            snap.machine_id_sha256,
        )

    def test_reads_thermal_load_memory_and_network_without_addresses(self) -> None:
        host = FakeHost()
        snap = self.adapter(host).read()

        self.assertEqual(61.25, snap.cpu_temp_c)
        self.assertEqual(12345.67, snap.uptime_s)
        self.assertEqual(
            (0.25, 0.50, 0.75),
            (snap.load_1m, snap.load_5m, snap.load_15m),
        )
        self.assertEqual(8178892, snap.memory_total_kib)
        self.assertEqual(6123456, snap.memory_available_kib)

        network = [x.to_dict() for x in snap.network_interfaces]
        self.assertEqual(
            [
                {"name": "eth0", "operstate": "up", "carrier": True},
                {"name": "wlan0", "operstate": "down", "carrier": False},
            ],
            network,
        )
        self.assertNotIn("address", str(network).lower())

    def test_decodes_vcgencmd_observations_without_claiming_safety(self) -> None:
        host = FakeHost()
        snap = self.adapter(host).read()

        self.assertEqual("0x50005", snap.throttled_raw)
        self.assertIn("under_voltage_now", snap.throttled_flags)
        self.assertIn("throttled_now", snap.throttled_flags)
        self.assertIn("under_voltage_occurred", snap.throttled_flags)
        self.assertIn("throttling_occurred", snap.throttled_flags)
        self.assertEqual(0.72, snap.core_voltage_v)
        serialized = json.dumps(snap.to_dict(), sort_keys=True)
        self.assertNotIn("10000000cafefeed", serialized)
        self.assertNotIn("0123456789abcdef0123456789abcdef", serialized)
        self.assertEqual(
            [
                ("vcgencmd", "get_throttled"),
                ("vcgencmd", "measure_volts", "core"),
            ],
            host.command_calls,
        )

    def test_missing_optional_sources_are_reported_not_fabricated(self) -> None:
        host = FakeHost()
        host.files.pop("/sys/class/thermal/thermal_zone0/temp")
        host.files.pop("/proc/device-tree/serial-number")
        host.commands.clear()

        snap = self.adapter(host).read()

        self.assertIsNone(snap.cpu_temp_c)
        self.assertIsNone(snap.core_voltage_v)
        self.assertIsNone(snap.throttled_raw)
        self.assertIsNone(snap.board_serial_sha256)
        self.assertIn("CPU temperature unavailable", snap.warnings)
        self.assertIn("vcgencmd throttling telemetry unavailable", snap.warnings)
        self.assertIn("board serial unavailable", snap.warnings)

    def test_non_pi_host_stays_observation_only(self) -> None:
        host = FakeHost()
        host.files["/proc/device-tree/model"] = "Generic ARM64 Board\x00"
        host.files["/proc/device-tree/compatible"] = "vendor,generic-arm64\x00"

        snap = self.adapter(host).read()
        self.assertFalse(snap.raspberry_pi_detected)
        self.assertIn(
            "host does not identify itself as Raspberry Pi",
            snap.warnings,
        )

    def test_observer_writes_receipt_without_changing_host_state(self) -> None:
        host = FakeHost()
        controller = PhysicalHostController(clock=fixed_clock)
        self.assertEqual(HostState.BOOT_SELFTEST, controller.state)

        receipt = PiTelemetryObserver(
            controller,
            self.adapter(host),
        ).observe()

        self.assertEqual(HostState.BOOT_SELFTEST, controller.state)
        self.assertEqual("observe", receipt["decision"])
        self.assertEqual("rpi_readonly_telemetry", receipt["event_kind"])
        self.assertTrue(receipt["inputs"]["raspberry_pi_detected"])
        self.assertTrue(controller.receipts.verify())

    def test_adapter_exposes_no_actuator_execution_surface(self) -> None:
        host = FakeHost()
        adapter = self.adapter(host)
        self.assertFalse(hasattr(adapter, "execute"))


if __name__ == "__main__":
    unittest.main()
