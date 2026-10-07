from __future__ import annotations

import hashlib
import json
import unittest

from runtime.physical_host.health_episodes import (
    EPISODE_CONTRACT,
    JOURNAL_CONTRACT,
)
from runtime.physical_host.nbg_memory_bridge import (
    NBG_SCHEMA_BLOB_SHA,
    NBG_SCHEMA_VERSION,
    journal_record_to_nbg_memory,
    nbg_fingerprint,
    validate_nbg_memory,
)


def journal_record() -> dict:
    episode = {
        "contract": EPISODE_CONTRACT,
        "episode_id": "episode-test-001",
        "host_identity": {
            "board_serial_sha256": "board-a",
            "machine_id_sha256": "machine-a",
        },
        "start_sequence": 4,
        "end_sequence": 8,
        "state": "closed",
        "peak_classification": "notable",
        "events": [],
        "close_reason": "stable_recovery",
        "authority_effect": "none",
    }
    envelope = {
        "contract": "phi-host-memory-envelope/v0.1",
        "kind": "host_health_episode",
        "episode_id": "episode-test-001",
        "host_identity": {
            "board_serial_sha256": "board-a",
            "machine_id_sha256": "machine-a",
        },
        "start_sequence": 4,
        "end_sequence": 8,
        "peak_classification": "notable",
        "signals": ["cpu_temp_c"],
        "new_flags": ["under_voltage_now"],
        "close_reason": "stable_recovery",
        "suggested_memory_role": "evidence",
        "authority_effect": "none",
    }
    body = {
        "contract": JOURNAL_CONTRACT,
        "episode": episode,
        "memory_envelope": envelope,
        "previous_hash": "0" * 64,
    }
    digest = hashlib.sha256(
        json.dumps(
            body,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
    return {**body, "current_hash": digest}


class NBGMemoryBridgeTests(unittest.TestCase):
    def test_fingerprint_matches_nbg_javascript_reference_vectors(self) -> None:
        self.assertEqual("fnv1a32:4f9f2cab", nbg_fingerprint("hello"))
        self.assertEqual("fnv1a32:a30d55d9", nbg_fingerprint("Φ"))
        self.assertEqual("fnv1a32:dd2c04d3", nbg_fingerprint("🧠"))

    def test_bridge_emits_nbg_epistemic_memory(self) -> None:
        memory = journal_record_to_nbg_memory(
            journal_record(),
            known_time={"basis": "test", "sequence": 9},
        )

        self.assertEqual(NBG_SCHEMA_VERSION, memory["schemaVersion"])
        self.assertEqual(
            "phipie:host-health:episode-test-001",
            memory["memoryId"],
        )
        self.assertEqual("INFERRED", memory["epistemic"]["origin"])
        self.assertTrue(memory["epistemic"]["authority"]["retainable"])
        self.assertTrue(memory["epistemic"]["authority"]["reasoningUsable"])
        self.assertFalse(memory["epistemic"]["authority"]["actionAuthorized"])
        self.assertFalse(
            memory["content"]["semanticBoundary"]["actionAuthorityGranted"]
        )
        self.assertEqual(
            {
                "basis": "phipie_host_sequence",
                "startSequence": 4,
                "endSequence": 8,
            },
            memory["validTime"],
        )
        self.assertEqual([], validate_nbg_memory(memory))

    def test_episode_is_inferred_not_observed(self) -> None:
        memory = journal_record_to_nbg_memory(journal_record())
        self.assertEqual("INFERRED", memory["epistemic"]["origin"])
        evidence = memory["epistemic"]["evidence"]
        self.assertEqual(1, len(evidence))
        self.assertEqual("OBSERVATION", evidence[0]["kind"])
        self.assertEqual(
            "derived_from_read_only_host_telemetry",
            evidence[0]["details"]["sourceRole"],
        )

    def test_bridge_pins_current_nbg_schema_blob(self) -> None:
        memory = journal_record_to_nbg_memory(journal_record())
        producer = memory["content"]["producer"]
        self.assertEqual(
            "56d39e4c9823ce4186affb5ea3a0df8783675121",
            NBG_SCHEMA_BLOB_SHA,
        )
        self.assertEqual(NBG_SCHEMA_BLOB_SHA, producer["nbgSchemaBlobSha"])

    def test_tampered_phi_journal_record_is_rejected(self) -> None:
        record = journal_record()
        record["episode"]["peak_classification"] = "stable"
        with self.assertRaises(ValueError):
            journal_record_to_nbg_memory(record)

    def test_episode_and_memory_envelope_must_refer_to_same_episode(self) -> None:
        record = journal_record()
        record["memory_envelope"]["episode_id"] = "episode-other"
        body = dict(record)
        body.pop("current_hash")
        record["current_hash"] = hashlib.sha256(
            json.dumps(
                body,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode("utf-8")
        ).hexdigest()

        with self.assertRaises(ValueError):
            journal_record_to_nbg_memory(record)

    def test_tampered_nbg_memory_fingerprint_is_detected(self) -> None:
        memory = journal_record_to_nbg_memory(journal_record())
        memory["content"]["semanticBoundary"]["stableMeansSafe"] = True
        errors = validate_nbg_memory(memory)
        self.assertIn("record fingerprint mismatch", errors)

    def test_confidence_is_bounded(self) -> None:
        with self.assertRaises(ValueError):
            journal_record_to_nbg_memory(journal_record(), confidence=1.1)


if __name__ == "__main__":
    unittest.main()
