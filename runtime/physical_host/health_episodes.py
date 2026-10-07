from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from .health_baseline import PiHealthDriftReport


EPISODE_CONTRACT = "phi-host-health-episode/v0.1"
JOURNAL_CONTRACT = "phi-host-health-journal/v0.1"

SEVERITY = {"stable": 0, "watch": 1, "notable": 2}


@dataclass(frozen=True)
class HealthEpisodeEvent:
    sequence: int
    classification: str
    metric_classifications: dict[str, str]
    new_flags: list[str]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HostHealthEpisode:
    episode_id: str
    host_identity: dict[str, str | None]
    start_sequence: int
    peak_classification: str
    events: list[HealthEpisodeEvent] = field(default_factory=list)
    end_sequence: int | None = None
    state: str = "open"
    close_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract": EPISODE_CONTRACT,
            "episode_id": self.episode_id,
            "host_identity": dict(self.host_identity),
            "start_sequence": self.start_sequence,
            "end_sequence": self.end_sequence,
            "state": self.state,
            "peak_classification": self.peak_classification,
            "events": [event.to_dict() for event in self.events],
            "close_reason": self.close_reason,
            "authority_effect": "none",
        }

    def memory_envelope(self) -> dict[str, Any]:
        signals = sorted(
            {
                name
                for event in self.events
                for name, level in event.metric_classifications.items()
                if level in {"watch", "notable"}
            }
        )
        flags = sorted(
            {
                flag
                for event in self.events
                for flag in event.new_flags
            }
        )
        return {
            "contract": "phi-host-memory-envelope/v0.1",
            "kind": "host_health_episode",
            "episode_id": self.episode_id,
            "host_identity": dict(self.host_identity),
            "start_sequence": self.start_sequence,
            "end_sequence": self.end_sequence,
            "peak_classification": self.peak_classification,
            "signals": signals,
            "new_flags": flags,
            "close_reason": self.close_reason,
            "suggested_memory_role": "evidence",
            "authority_effect": "none",
        }


class HostHealthEpisodeTracker:
    def __init__(
        self,
        *,
        host_identity: dict[str, str | None],
        recovery_samples: int = 2,
    ) -> None:
        if recovery_samples < 1:
            raise ValueError("recovery_samples must be at least 1")
        self.host_identity = dict(host_identity)
        self.recovery_samples = recovery_samples
        self.sequence = 0
        self.recovery_streak = 0
        self.active: HostHealthEpisode | None = None

    @staticmethod
    def _event(
        sequence: int,
        report: PiHealthDriftReport,
    ) -> HealthEpisodeEvent:
        return HealthEpisodeEvent(
            sequence=sequence,
            classification=report.classification,
            metric_classifications={
                name: metric.classification
                for name, metric in report.metrics.items()
            },
            new_flags=list(report.new_throttled_flags),
            warnings=list(report.warnings),
        )

    def update(self, report: PiHealthDriftReport) -> dict[str, Any]:
        self.sequence += 1
        event = self._event(self.sequence, report)

        if report.classification == "identity_mismatch":
            if self.active is None:
                return self._result("identity_mismatch_refused")
            self.active.events.append(event)
            self.active.state = "aborted"
            self.active.end_sequence = event.sequence
            self.active.close_reason = "identity_mismatch"
            closed = self.active
            self.active = None
            self.recovery_streak = 0
            return self._result("episode_aborted", closed=closed)

        if report.classification in {"watch", "notable"}:
            self.recovery_streak = 0
            if self.active is None:
                self.active = HostHealthEpisode(
                    episode_id=f"episode-{uuid4()}",
                    host_identity=dict(self.host_identity),
                    start_sequence=event.sequence,
                    peak_classification=event.classification,
                    events=[event],
                )
                return self._result("episode_opened")

            self.active.events.append(event)
            if (
                SEVERITY[event.classification]
                > SEVERITY.get(self.active.peak_classification, 0)
            ):
                self.active.peak_classification = event.classification
            return self._result("episode_updated")

        if report.classification == "stable":
            if self.active is None:
                return self._result("stable_no_episode")

            self.active.events.append(event)
            self.recovery_streak += 1
            if self.recovery_streak < self.recovery_samples:
                return self._result("episode_recovering")

            self.active.state = "closed"
            self.active.end_sequence = event.sequence
            self.active.close_reason = "stable_recovery"
            closed = self.active
            self.active = None
            self.recovery_streak = 0
            return self._result("episode_closed", closed=closed)

        if self.active is not None:
            self.active.events.append(event)
            return self._result("episode_observation_gap")

        return self._result("observation_gap_no_episode")

    def _result(
        self,
        transition: str,
        *,
        closed: HostHealthEpisode | None = None,
    ) -> dict[str, Any]:
        return {
            "transition": transition,
            "active_episode": self.active,
            "closed_episode": closed,
            "authority_effect": "none",
        }


class HostHealthJournal:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    @staticmethod
    def _canonical(payload: dict[str, Any]) -> bytes:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")

    def _head(self) -> str:
        records = self.records()
        if not records:
            return "0" * 64
        return str(records[-1]["current_hash"])

    def append(self, episode: HostHealthEpisode) -> dict[str, Any]:
        if episode.state not in {"closed", "aborted"}:
            raise ValueError("only completed episodes may be journaled")

        body = {
            "contract": JOURNAL_CONTRACT,
            "episode": episode.to_dict(),
            "memory_envelope": episode.memory_envelope(),
            "previous_hash": self._head(),
        }
        digest = hashlib.sha256(self._canonical(body)).hexdigest()
        record = {**body, "current_hash": digest}

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        return record

    def records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [
            json.loads(line)
            for line in self.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def verify(self) -> bool:
        previous = "0" * 64
        for record in self.records():
            current = record.get("current_hash")
            body = dict(record)
            body.pop("current_hash", None)
            if body.get("previous_hash") != previous:
                return False
            expected = hashlib.sha256(self._canonical(body)).hexdigest()
            if current != expected:
                return False
            previous = str(current)
        return True
