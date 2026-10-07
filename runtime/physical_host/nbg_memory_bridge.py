from __future__ import annotations

import hashlib
import json
from typing import Any

from .health_episodes import EPISODE_CONTRACT, JOURNAL_CONTRACT


NBG_SCHEMA_VERSION = "NBG_EPISTEMIC_1"
NBG_SCHEMA_SOURCE = (
    "MichaelWave369/NestedBubbleGear:"
    "schemas/epistemic-memory.schema.json"
)
NBG_SCHEMA_BLOB_SHA = "56d39e4c9823ce4186affb5ea3a0df8783675121"

_ALLOWED_ORIGINS = {
    "OBSERVED",
    "VERIFIED",
    "INFERRED",
    "DREAMED",
    "SIMULATED",
    "UNKNOWN",
}


def _stable_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def nbg_fingerprint(value: Any) -> str:
    """Match NestedBubbleGear's browser-side FNV-1a 32 fingerprint.

    NBG's JavaScript implementation hashes UTF-16 code units via charCodeAt().
    Encoding to UTF-16 little-endian and iterating two bytes at a time preserves
    that behavior for non-ASCII text as well.
    """

    text = value if isinstance(value, str) else _stable_json(value)
    raw = text.encode("utf-16-le", errors="surrogatepass")

    hash_value = 2166136261
    for index in range(0, len(raw), 2):
        code_unit = raw[index] | (raw[index + 1] << 8)
        hash_value ^= code_unit
        hash_value = (hash_value * 16777619) & 0xFFFFFFFF

    return f"fnv1a32:{hash_value:08x}"


def _normalized_evidence(
    *,
    evidence_id: str,
    source: dict[str, Any],
    known_time: Any,
    valid_time: Any,
    details: dict[str, Any],
) -> dict[str, Any]:
    body = {
        "evidenceId": evidence_id,
        "kind": "OBSERVATION",
        "source": source,
        "knownTime": known_time,
        "validTime": valid_time,
        "details": details,
    }
    return {
        **body,
        "evidenceFingerprint": nbg_fingerprint(body),
    }


def _require_hex_sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{field} must be a 64-character SHA-256 hex string")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{field} must be hexadecimal") from exc
    return value.lower()


def _validate_journal_integrity(record: dict[str, Any]) -> str:
    current_hash = _require_hex_sha256(record.get("current_hash"), "current_hash")
    body = dict(record)
    body.pop("current_hash", None)
    expected = hashlib.sha256(
        json.dumps(
            body,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
    if current_hash != expected:
        raise ValueError("PhiPie episode journal record hash mismatch")
    return current_hash


def journal_record_to_nbg_memory(
    journal_record: dict[str, Any],
    *,
    confidence: float = 0.5,
    known_time: Any = None,
) -> dict[str, Any]:
    """Convert one completed PhiPie health episode into NBG epistemic memory.

    The episode is INFERRED because episode boundaries and drift classes are a
    deterministic interpretation over observed telemetry, not raw observation
    themselves. The resulting memory is retainable and reasoning-usable but
    never action-authorized.
    """

    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        raise ValueError("confidence must be numeric")
    confidence = float(confidence)
    if confidence < 0.0 or confidence > 1.0:
        raise ValueError("confidence must be in [0, 1]")

    if journal_record.get("contract") != JOURNAL_CONTRACT:
        raise ValueError("unsupported PhiPie episode journal contract")

    episode = journal_record.get("episode")
    envelope = journal_record.get("memory_envelope")
    if not isinstance(episode, dict) or not isinstance(envelope, dict):
        raise ValueError("journal record must contain episode and memory_envelope")

    if episode.get("contract") != EPISODE_CONTRACT:
        raise ValueError("unsupported PhiPie episode contract")
    if envelope.get("kind") != "host_health_episode":
        raise ValueError("unsupported memory envelope kind")
    if envelope.get("authority_effect") != "none":
        raise ValueError("physical memory envelope must have no authority effect")

    episode_id = episode.get("episode_id")
    if not isinstance(episode_id, str) or not episode_id:
        raise ValueError("episode_id is required")

    journal_hash = _validate_journal_integrity(journal_record)

    if envelope.get("episode_id") != episode_id:
        raise ValueError("episode and memory envelope identity mismatch")

    start_sequence = episode.get("start_sequence")
    end_sequence = episode.get("end_sequence")
    valid_time = {
        "basis": "phipie_host_sequence",
        "startSequence": start_sequence,
        "endSequence": end_sequence,
    }

    memory_id = f"phipie:host-health:{episode_id}"
    evidence_id = f"phipie:episode-journal:{journal_hash[:16]}"

    evidence = _normalized_evidence(
        evidence_id=evidence_id,
        source={
            "system": "PhiPie",
            "journalContract": JOURNAL_CONTRACT,
            "episodeContract": EPISODE_CONTRACT,
            "journalRecordHash": journal_hash,
        },
        known_time=known_time,
        valid_time=valid_time,
        details={
            "episodeId": episode_id,
            "state": episode.get("state"),
            "peakClassification": episode.get("peak_classification"),
            "closeReason": episode.get("close_reason"),
            "sourceRole": "derived_from_read_only_host_telemetry",
        },
    )

    record = {
        "schemaVersion": NBG_SCHEMA_VERSION,
        "memoryId": memory_id,
        "content": {
            "kind": "PHIPIE_HOST_HEALTH_EPISODE",
            "episode": envelope,
            "producer": {
                "system": "PhiPie",
                "bridgeContract": "phipie-nbg-memory-bridge/v0.1",
                "nbgSchemaSource": NBG_SCHEMA_SOURCE,
                "nbgSchemaBlobSha": NBG_SCHEMA_BLOB_SHA,
            },
            "semanticBoundary": {
                "episodeIsFault": False,
                "stableMeansSafe": False,
                "actionAuthorityGranted": False,
            },
        },
        "epistemic": {
            "origin": "INFERRED",
            "confidence": confidence,
            "evidence": [evidence],
            "lineage": {
                "rootMemoryId": memory_id,
                "parentMemoryId": None,
                "transitionReceiptIds": [],
                "sourceMemoryIds": [],
                "compactedFrom": [],
            },
            "authority": {
                "retainable": True,
                "reasoningUsable": True,
                "actionAuthorized": False,
            },
        },
        "validTime": valid_time,
        "knownTime": known_time,
        "tags": sorted(
            {
                "evidence",
                "host-health",
                "inferred",
                "phipie",
                "physical-episode",
            }
        ),
    }

    return {
        **record,
        "recordFingerprint": nbg_fingerprint(record),
    }


def validate_nbg_memory(record: dict[str, Any]) -> list[str]:
    """Validate the subset of NBG_EPISTEMIC_1 emitted by this bridge."""

    errors: list[str] = []

    if record.get("schemaVersion") != NBG_SCHEMA_VERSION:
        errors.append("schemaVersion mismatch")
    if not isinstance(record.get("memoryId"), str) or not record.get("memoryId"):
        errors.append("memoryId required")

    epistemic = record.get("epistemic")
    if not isinstance(epistemic, dict):
        errors.append("epistemic object required")
        return errors

    if epistemic.get("origin") not in _ALLOWED_ORIGINS:
        errors.append("unsupported epistemic origin")

    confidence = epistemic.get("confidence")
    if (
        not isinstance(confidence, (int, float))
        or isinstance(confidence, bool)
        or confidence < 0
        or confidence > 1
    ):
        errors.append("confidence must be in [0, 1]")

    authority = epistemic.get("authority")
    if authority != {
        "retainable": True,
        "reasoningUsable": True,
        "actionAuthorized": False,
    }:
        errors.append("bridge authority envelope changed")

    lineage = epistemic.get("lineage")
    if not isinstance(lineage, dict):
        errors.append("lineage object required")
    else:
        required_lineage = {
            "rootMemoryId",
            "parentMemoryId",
            "transitionReceiptIds",
            "sourceMemoryIds",
            "compactedFrom",
        }
        if set(lineage) != required_lineage:
            errors.append("lineage keys mismatch")

    evidence = epistemic.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        errors.append("evidence required")
    else:
        for row in evidence:
            if not isinstance(row, dict):
                errors.append("evidence row must be object")
                continue
            body = dict(row)
            fingerprint = body.pop("evidenceFingerprint", None)
            if fingerprint != nbg_fingerprint(body):
                errors.append("evidence fingerprint mismatch")

    body = dict(record)
    fingerprint = body.pop("recordFingerprint", None)
    if fingerprint != nbg_fingerprint(body):
        errors.append("record fingerprint mismatch")

    return errors
