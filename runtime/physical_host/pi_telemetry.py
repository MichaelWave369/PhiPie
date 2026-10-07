from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from .model import PhysicalHostController


TextReader = Callable[[str], str | None]
DirLister = Callable[[str], list[str]]
CommandRunner = Callable[[list[str]], str | None]


THROTTLE_BITS: dict[int, str] = {
    0: "under_voltage_now",
    1: "frequency_capped_now",
    2: "throttled_now",
    3: "soft_temperature_limit_now",
    16: "under_voltage_occurred",
    17: "frequency_capped_occurred",
    18: "throttling_occurred",
    19: "soft_temperature_limit_occurred",
}


def _default_read_text(path: str) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except (FileNotFoundError, PermissionError, IsADirectoryError, OSError):
        return None


def _default_listdir(path: str) -> list[str]:
    try:
        return sorted(os.listdir(path))
    except (FileNotFoundError, PermissionError, NotADirectoryError, OSError):
        return []


def _default_run_command(argv: list[str]) -> str | None:
    try:
        completed = subprocess.run(
            argv,
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (FileNotFoundError, PermissionError, subprocess.SubprocessError, OSError):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.replace("\x00", "").replace("\\\\x00", "").strip()
    return cleaned or None


def _sha256_text(value: str | None) -> str | None:
    cleaned = _clean(value)
    if cleaned is None:
        return None
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()


def _parse_float(value: str | None) -> float | None:
    cleaned = _clean(value)
    if cleaned is None:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_int(value: str | None) -> int | None:
    cleaned = _clean(value)
    if cleaned is None:
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


def _parse_meminfo(text: str | None) -> tuple[int | None, int | None]:
    if text is None:
        return None, None
    values: dict[str, int] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, raw = line.split(":", 1)
        token = raw.strip().split()[0] if raw.strip() else ""
        try:
            values[key] = int(token)
        except ValueError:
            continue
    return values.get("MemTotal"), values.get("MemAvailable")


def _parse_loadavg(text: str | None) -> tuple[float | None, float | None, float | None]:
    cleaned = _clean(text)
    if cleaned is None:
        return None, None, None
    fields = cleaned.split()
    if len(fields) < 3:
        return None, None, None
    try:
        return float(fields[0]), float(fields[1]), float(fields[2])
    except ValueError:
        return None, None, None


def _parse_vcgencmd_value(text: str | None, prefix: str) -> float | None:
    cleaned = _clean(text)
    if cleaned is None or not cleaned.startswith(prefix):
        return None
    raw = cleaned[len(prefix):]
    raw = raw.replace("V", "").replace("'C", "").strip()
    try:
        return float(raw)
    except ValueError:
        return None


def _parse_throttled(text: str | None) -> tuple[str | None, list[str]]:
    cleaned = _clean(text)
    if cleaned is None:
        return None, []
    if "=" in cleaned:
        _, raw = cleaned.split("=", 1)
    else:
        raw = cleaned
    raw = raw.strip().lower()
    try:
        value = int(raw, 16)
    except ValueError:
        return raw, []
    flags = [name for bit, name in THROTTLE_BITS.items() if value & (1 << bit)]
    return f"0x{value:x}", flags


@dataclass(frozen=True)
class NetworkInterfaceObservation:
    name: str
    operstate: str | None
    carrier: bool | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PiTelemetrySnapshot:
    raspberry_pi_detected: bool
    model: str | None
    compatible: list[str]
    board_serial_sha256: str | None
    machine_id_sha256: str | None
    cpu_temp_c: float | None
    uptime_s: float | None
    load_1m: float | None
    load_5m: float | None
    load_15m: float | None
    memory_total_kib: int | None
    memory_available_kib: int | None
    throttled_raw: str | None
    throttled_flags: list[str]
    core_voltage_v: float | None
    network_interfaces: list[NetworkInterfaceObservation]
    provenance: dict[str, str]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["network_interfaces"] = [
            interface.to_dict() for interface in self.network_interfaces
        ]
        return data


class RaspberryPiTelemetryAdapter:
    """Read-only host telemetry probe for Raspberry Pi-class Linux systems.

    The adapter intentionally exposes observations only. It does not implement
    a Safety SensorAdapter and its values must not be treated as calibrated
    Plane A safety inputs without a later qualification step.
    """

    def __init__(
        self,
        *,
        read_text: TextReader = _default_read_text,
        listdir: DirLister = _default_listdir,
        run_command: CommandRunner = _default_run_command,
    ) -> None:
        self.read_text = read_text
        self.listdir = listdir
        self.run_command = run_command

    def _compatible(self) -> list[str]:
        raw = self.read_text("/proc/device-tree/compatible")
        if raw is None:
            return []
        normalized = raw.replace("\\\\x00", "\x00")\n        return [part.strip() for part in normalized.split("\x00") if part.strip()]

    def _serial(self) -> str | None:
        direct = _clean(self.read_text("/proc/device-tree/serial-number"))
        if direct:
            return direct

        cpuinfo = self.read_text("/proc/cpuinfo")
        if cpuinfo:
            for line in cpuinfo.splitlines():
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                if key.strip().lower() == "serial":
                    return _clean(value)
        return None

    def _cpu_temp_c(self) -> float | None:
        raw = _parse_float(self.read_text("/sys/class/thermal/thermal_zone0/temp"))
        if raw is None:
            return None
        return raw / 1000.0 if raw > 1000 else raw

    def _uptime_s(self) -> float | None:
        raw = _clean(self.read_text("/proc/uptime"))
        if raw is None:
            return None
        first = raw.split()[0] if raw.split() else ""
        try:
            return float(first)
        except ValueError:
            return None

    def _network(self) -> list[NetworkInterfaceObservation]:
        observations: list[NetworkInterfaceObservation] = []
        for name in self.listdir("/sys/class/net"):
            if not name or "/" in name or name == "lo":
                continue
            operstate = _clean(self.read_text(f"/sys/class/net/{name}/operstate"))
            carrier_raw = _parse_int(self.read_text(f"/sys/class/net/{name}/carrier"))
            carrier = None if carrier_raw is None else carrier_raw == 1
            observations.append(
                NetworkInterfaceObservation(
                    name=name,
                    operstate=operstate,
                    carrier=carrier,
                )
            )
        return observations

    def read(self) -> PiTelemetrySnapshot:
        model = _clean(self.read_text("/proc/device-tree/model"))
        compatible = self._compatible()
        serial = self._serial()
        machine_id = _clean(self.read_text("/etc/machine-id"))
        cpu_temp_c = self._cpu_temp_c()

        load_1m, load_5m, load_15m = _parse_loadavg(
            self.read_text("/proc/loadavg")
        )
        mem_total, mem_available = _parse_meminfo(
            self.read_text("/proc/meminfo")
        )

        throttled_text = self.run_command(["vcgencmd", "get_throttled"])
        throttled_raw, throttled_flags = _parse_throttled(throttled_text)
        core_voltage_v = _parse_vcgencmd_value(
            self.run_command(["vcgencmd", "measure_volts", "core"]),
            "volt=",
        )

        model_l = (model or "").lower()
        compatible_l = " ".join(compatible).lower()
        detected = "raspberry pi" in model_l or "raspberrypi" in compatible_l

        warnings: list[str] = []
        if not detected:
            warnings.append("host does not identify itself as Raspberry Pi")
        if cpu_temp_c is None:
            warnings.append("CPU temperature unavailable")
        if throttled_raw is None:
            warnings.append("vcgencmd throttling telemetry unavailable")
        if core_voltage_v is None:
            warnings.append("vcgencmd core-voltage telemetry unavailable")
        if serial is None:
            warnings.append("board serial unavailable")

        provenance = {
            "model": "/proc/device-tree/model",
            "compatible": "/proc/device-tree/compatible",
            "board_serial": "/proc/device-tree/serial-number or /proc/cpuinfo",
            "machine_id": "/etc/machine-id",
            "cpu_temp": "/sys/class/thermal/thermal_zone0/temp",
            "uptime": "/proc/uptime",
            "load": "/proc/loadavg",
            "memory": "/proc/meminfo",
            "network": "/sys/class/net/*/{operstate,carrier}",
            "throttled": "vcgencmd get_throttled",
            "core_voltage": "vcgencmd measure_volts core",
        }

        return PiTelemetrySnapshot(
            raspberry_pi_detected=detected,
            model=model,
            compatible=compatible,
            board_serial_sha256=_sha256_text(serial),
            machine_id_sha256=_sha256_text(machine_id),
            cpu_temp_c=cpu_temp_c,
            uptime_s=self._uptime_s(),
            load_1m=load_1m,
            load_5m=load_5m,
            load_15m=load_15m,
            memory_total_kib=mem_total,
            memory_available_kib=mem_available,
            throttled_raw=throttled_raw,
            throttled_flags=throttled_flags,
            core_voltage_v=core_voltage_v,
            network_interfaces=self._network(),
            provenance=provenance,
            warnings=warnings,
        )


class PiTelemetryObserver:
    """Writes read-only Raspberry Pi observations into the existing receipt chain."""

    def __init__(
        self,
        controller: PhysicalHostController,
        telemetry: RaspberryPiTelemetryAdapter,
    ) -> None:
        self.controller = controller
        self.telemetry = telemetry

    def observe(self) -> dict[str, Any]:
        snapshot = self.telemetry.read()
        state = self.controller.state
        return self.controller.receipts.append(
            source_plane="platform",
            event_kind="rpi_readonly_telemetry",
            state_before=state,
            state_after=state,
            inputs=snapshot.to_dict(),
            decision="observe",
            action=None,
            reason=(
                "read-only Raspberry Pi host telemetry; "
                "not calibrated Plane A safety authority"
            ),
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read non-qualifying Raspberry Pi host telemetry."
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="pretty-print JSON",
    )
    args = parser.parse_args()

    snapshot = RaspberryPiTelemetryAdapter().read()
    payload = snapshot.to_dict()
    payload["qualification_claim"] = False
    payload["safety_authority"] = False

    if args.pretty:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
