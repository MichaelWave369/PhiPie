from __future__ import annotations

import unittest

from runtime.physical_host.health_baseline import (
    MetricDrift,
    PiHealthDriftReport,
)
from runtime.physical_host.health_episodes import HostHealthEpisodeTracker


IDENTITY = {
    "board_serial_sha256": "board-a",
    "machine_id_sha256": "machine-a",
}


def report(
    classification: str,
    *,
    metric_classification: str | None = None,
) -> PiHealthDriftReport:
    metrics = {}
    if metric_classification:
        magnitude = 7.0 if metric_classification == "notable" else 4.0
        metrics["cpu_temp_c"] = MetricDrift(
            observed=60.0,
            baseline_median=50.0,
            scale=2.0,
            signed_score=magnitude,
            magnitude_score=magnitude,
            direction="above",
            classification=metric_classification,
        )
    return PiHealthDriftReport(
        classification=classification,
        identity_match=False if classification == "identity_mismatch" else True,
        metrics=metrics,
        new_throttled_flags=[],
        warnings=[],
    )


class HostHealthEpisodeTests(unittest.TestCase):
    def tracker(self) -> HostHealthEpisodeTracker:
        return HostHealthEpisodeTracker(
            host_identity=IDENTITY,
            recovery_samples=2,
        )

    def test_stable_does_not_open_episode(self) -> None:
        result = self.tracker().update(report("stable"))
        self.assertEqual("stable_no_episode", result["transition"])
        self.assertIsNone(result["active_episode"])

    def test_watch_opens_and_notable_escalates(self) -> None:
        tracker = self.tracker()
        opened = tracker.update(report("watch", metric_classification="watch"))
        self.assertEqual("episode_opened", opened["transition"])

        updated = tracker.update(
            report("notable", metric_classification="notable")
        )
        self.assertEqual("episode_updated", updated["transition"])
        self.assertEqual(
            "notable",
            updated["active_episode"].peak_classification,
        )

    def test_two_stable_samples_close_episode(self) -> None:
        tracker = self.tracker()
        tracker.update(report("notable"))
        first = tracker.update(report("stable"))
        self.assertEqual("episode_recovering", first["transition"])

        second = tracker.update(report("stable"))
        self.assertEqual("episode_closed", second["transition"])
        self.assertEqual(
            "stable_recovery",
            second["closed_episode"].close_reason,
        )

    def test_gap_does_not_close_episode(self) -> None:
        tracker = self.tracker()
        tracker.update(report("watch"))
        gap = tracker.update(report("insufficient_observation"))
        self.assertEqual("episode_observation_gap", gap["transition"])
        self.assertIsNotNone(gap["active_episode"])

    def test_identity_mismatch_aborts_episode(self) -> None:
        tracker = self.tracker()
        tracker.update(report("watch"))
        result = tracker.update(report("identity_mismatch"))
        self.assertEqual("episode_aborted", result["transition"])
        self.assertEqual(
            "identity_mismatch",
            result["closed_episode"].close_reason,
        )

    def test_memory_envelope_has_no_authority(self) -> None:
        tracker = self.tracker()
        tracker.update(report("watch", metric_classification="watch"))
        tracker.update(report("stable"))
        closed = tracker.update(report("stable"))["closed_episode"]
        envelope = closed.memory_envelope()

        self.assertEqual("host_health_episode", envelope["kind"])
        self.assertEqual("evidence", envelope["suggested_memory_role"])
        self.assertEqual("none", envelope["authority_effect"])


if __name__ == "__main__":
    unittest.main()
