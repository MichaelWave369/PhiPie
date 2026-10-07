from __future__ import annotations

import argparse
import json
import statistics
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .model import PhysicalHostController
from .pi_telemetry import PiTelemetrySnapshot, RaspberryPiTelemetryAdapter


BASELINE_CONTRACT = "phi-pi-health-baseline/v0.1"
MIN_BASELINE_SAMPLES = 5

METRIC_FLOORS: dict[str, float] = {
    "cpu_temp_c": 1.0,
    "load_1m": 0.10,
    "memory_available_ratio": 0.02,
    "core_voltage_v": 0.02,
    "carrier_up_count": 1.0,
}


def _identity(snapshot: PiTelemetrySnapshot) -> dict[str, str | None]:
    return {
        "board_serial_sha256": snapshot.board_serial_sha256,
        "machine_id_sha256": snapshot.machine_id_sha256,
    }


def _identity_matches(
    baseline_identity: dict[str, str | None],
    snapshot: PiTelemetrySnapshot,
) -> bool | None:
    observed = _identity(snapshot)
    comparable = False

    for key in ("board_serial_sha256", "machine_id_sha256"):
        expected = baseline_identity.get(key)
        actual = observed.get(key)
        if expected is None or actual is None:
            continue
        comparable = True
        if expected != actual:
            return False

    return True if comparable else None


def _metric_values(snapshot: PiTelemetrySnapshot) -> dict[str, float | None]:
    memory_ratio: float | None = None
    if (
        snapshot.memory_total_kib is not None
        and snapshot.memory_available_kib is not None
        and snapshot.memory_total_kib > 0
    ):
        memory_ratio = snapshot.memory_available_kib / snapshot.memory_total_kib

    carrier_up_count = float(
        sum(1 for item in snapshot.network_interfaces if item.carrier is True)
    )

    return {
        "cpu_temp_c": snapshot.cpu_temp_c,
        "load_1m": snapshot.load_1m,
        "memory_available_ratio": memory_ratio,
        "core_voltage_v": snapshot.core_voltage_v,
        "carrier_up_count": carrier_up_count,
    }


@dataclass(frozen=True)
class MetricBaseline:
    count: int
    median: float
    mad: float
    scale: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MetricBaseline":
        return cls(
            count=int(data["count"]),
            median=float(data["median"]),
            mad=float(data["mad"]),
            scale=float(data["scale"]),
        )


@dataclass(frozen=True)
class MetricDrift:
    observed: float
    baseline_median: float
    scale: float
    signed_score: float
    magnitude_score: float
    direction: str
    classification: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PiHealthDriftReport:
    classification: str
    identity_match: bool | None
    metrics: dict[str, MetricDrift]
    new_throttled_flags: list[str]
    warnings: list[str]
    authority_effect: str = "none"

    def to_dict(self) -> dict[str, Any]:
        return {
            "classification": self.classification,
            "identity_match": self.identity_match,
            "metrics": {
                name: report.to_dict() for name, report in self.metrics.items()
            },
            "new_throttled_flags": list(self.new_throttled_flags),
            "warnings": list(self.warnings),
            "authority_effect": self.authority_effect,
        }


@dataclass(frozen=True)
class PiHealthBaseline:
    contract: str
    sample_count: int
    identity: dict[str, str | None]
    metrics: dict[str, MetricBaseline]
    observed_throttled_flags: list[str]
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract": self.contract,
            "sample_count": self.sample_count,
            "identity": dict(self.identity),
            "metrics": {
                name: baseline.to_dict()
                for name, baseline in self.metrics.items()
            },
            "observed_throttled_flags": list(self.observed_throttled_flags),
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PiHealthBaseline":
        if data.get("contract") != BASELINE_CONTRACT:
            raise ValueError(
                f"unsupported baseline contract: {data.get('contract')!r}"
            )
        return cls(
            contract=BASELINE_CONTRACT,
            sample_count=int(data["sample_count"]),
            identity=dict(data.get("identity") or {}),
            metrics={
                name: MetricBaseline.from_dict(value)
                for name, value in (data.get("metrics") or {}).items()
            },
            observed_throttled_flags=sorted(
                str(flag)
                for flag in data.get("observed_throttled_flags", [])
            ),
            notes=[str(note) for note in data.get("notes", [])],
        )

    def evaluate(self, snapshot: PiTelemetrySnapshot) -> PiHealthDriftReport:
        identity_match = _identity_matches(self.identity, snapshot)
        warnings: list[str] = []

        if identity_match is False:
            return PiHealthDriftReport(
                classification="identity_mismatch",
                identity_match=False,
                metrics={},
                new_throttled_flags=[],
                warnings=[
                    "snapshot identity does not match baseline identity; "
                    "drift scoring refused"
                ],
            )

        if identity_match is None:
            warnings.append(
                "baseline identity could not be compared; "
                "drift remains observation-only"
            )

        observed_metrics = _metric_values(snapshot)
        reports: dict[str, MetricDrift] = {}
        rank = {"stable": 0, "watch": 1, "notable": 2}
        overall = "stable"

        for name, baseline in self.metrics.items():
            observed = observed_metrics.get(name)
            if observed is None:
                warnings.append(f"{name} unavailable for drift comparison")
                continue

            signed = (float(observed) - baseline.median) / baseline.scale
            magnitude = abs(signed)
            if magnitude >= 6.0:
                classification = "notable"
            elif magnitude >= 3.0:
                classification = "watch"
            else:
                classification = "stable"

            if rank[classification] > rank[overall]:
                overall = classification

            if signed > 0:
                direction = "above"
            elif signed < 0:
                direction = "below"
            else:
                direction = "at"

            reports[name] = MetricDrift(
                observed=float(observed),
                baseline_median=baseline.median,
                scale=baseline.scale,
                signed_score=signed,
                magnitude_score=magnitude,
                direction=direction,
                classification=classification,
            )

        baseline_flags = set(self.observed_throttled_flags)
        new_flags = sorted(set(snapshot.throttled_flags).difference(baseline_flags))
        if new_flags:
            overall = "notable"

        if not reports:
            overall = "insufficient_observation"
            warnings.append("no baseline metric had a comparable observation")

        return PiHealthDriftReport(
            classification=overall,
            identity_match=identity_match,
            metrics=reports,
            new_throttled_flags=new_flags,
            warnings=warnings,
        )


class PiHealthBaselineBuilder:
    def __init__(self, *, min_samples: int = MIN_BASELINE_SAMPLES) -> None:
        if min_samples < 2:
            raise ValueError("min_samples must be at least 2")
        self.min_samples = min_samples
        self.snapshots: list[PiTelemetrySnapshot] = []
        self.identity: dict[str, str | None] | None = None

    def add(self, snapshot: PiTelemetrySnapshot) -> None:
        current_identity = _identity(snapshot)

        if self.identity is None:
            self.identity = current_identity
        else:
            for key in ("board_serial_sha256", "machine_id_sha256"):
                expected = self.identity.get(key)
                actual = current_identity.get(key)
                if expected is not None and actual is not None and expected != actual:
                    raise ValueError(
                        f"baseline identity changed for {key}; "
                        "refusing to mix hosts"
                    )
                if expected is None and actual is not None:
                    self.identity[key] = actual

        self.snapshots.append(snapshot)

    def finalize(self) -> PiHealthBaseline:
        if len(self.snapshots) < self.min_samples:
            raise ValueError(
                f"need at least {self.min_samples} samples; "
                f"have {len(self.snapshots)}"
            )

        metrics: dict[str, MetricBaseline] = {}
        for name, floor in METRIC_FLOORS.items():
            values: list[float] = []
            for snapshot in self.snapshots:
                value = _metric_values(snapshot).get(name)
                if value is not None:
                    values.append(float(value))

            if len(values) < self.min_samples:
                continue

            center = float(statistics.median(values))
            deviations = [abs(value - center) for value in values]
            mad = float(statistics.median(deviations))
            robust_scale = mad * 1.4826
            scale = max(robust_scale, floor)

            metrics[name] = MetricBaseline(
                count=len(values),
                median=center,
                mad=mad,
                scale=scale,
            )

        if not metrics:
            raise ValueError(
                "baseline has no metric with enough comparable observations"
            )

        flags = sorted(
            {
                flag
                for snapshot in self.snapshots
                for flag in snapshot.throttled_flags
            }
        )

        notes: list[str] = [
            "heuristic observation baseline only",
            "baseline drift does not grant safety or actuator authority",
        ]
        if not any((self.identity or {}).values()):
            notes.append("baseline has no comparable host identity")

        return PiHealthBaseline(
            contract=BASELINE_CONTRACT,
            sample_count=len(self.snapshots),
            identity=self.identity or {
                "board_serial_sha256": None,
                "machine_id_sha256": None,
            },
            metrics=metrics,
            observed_throttled_flags=flags,
            notes=notes,
        )


class PiHealthObserver:
    """Advisory baseline/drift observer with zero physical authority."""

    def __init__(
        self,
        controller: PhysicalHostController,
        telemetry: RaspberryPiTelemetryAdapter,
        baseline: PiHealthBaseline,
    ) -> None:
        self.controller = controller
        self.telemetry = telemetry
        self.baseline = baseline

    def observe(self) -> dict[str, Any]:
        snapshot = self.telemetry.read()
        report = self.baseline.evaluate(snapshot)
        state = self.controller.state

        receipt = self.controller.receipts.append(
            source_plane="diagnostic",
            event_kind="rpi_health_drift",
            state_before=state,
            state_after=state,
            inputs={
                "telemetry": snapshot.to_dict(),
                "baseline_contract": self.baseline.contract,
                "baseline_sample_count": self.baseline.sample_count,
            },
            decision="observe",
            action=None,
            reason=(
                "advisory host-health drift assessment only; "
                f"classification={report.classification}; "
                "no safety-state transition or actuator authority"
            ),
            evidence_refs=[],
        )
        return {**receipt, "diagnostic_report": report.to_dict()}


def _load_baseline(path: str) -> PiHealthBaseline:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return PiHealthBaseline.from_dict(data)


def _write_json(path: str, data: dict[str, Any]) -> None:
    Path(path).write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture or compare non-qualifying PhiPie health baselines."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    capture = sub.add_parser("capture")
    capture.add_argument("--samples", type=int, default=5)
    capture.add_argument("--interval", type=float, default=1.0)
    capture.add_argument("--out", required=True)

    check = sub.add_parser("check")
    check.add_argument("--baseline", required=True)
    check.add_argument("--pretty", action="store_true")

    args = parser.parse_args()
    telemetry = RaspberryPiTelemetryAdapter()

    if args.command == "capture":
        if args.samples < MIN_BASELINE_SAMPLES:
            parser.error(
                f"--samples must be at least {MIN_BASELINE_SAMPLES}"
            )
        if args.interval < 0:
            parser.error("--interval must be non-negative")

        builder = PiHealthBaselineBuilder(min_samples=args.samples)
        for index in range(args.samples):
            builder.add(telemetry.read())
            if index + 1 < args.samples and args.interval:
                time.sleep(args.interval)

        baseline = builder.finalize()
        _write_json(args.out, baseline.to_dict())
        print(
            json.dumps(
                {
                    "written": args.out,
                    "sample_count": baseline.sample_count,
                    "qualification_claim": False,
                    "safety_authority": False,
                },
                sort_keys=True,
            )
        )
        return 0

    baseline = _load_baseline(args.baseline)
    report = baseline.evaluate(telemetry.read()).to_dict()
    report["qualification_claim"] = False
    report["safety_authority"] = False
    if args.pretty:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
