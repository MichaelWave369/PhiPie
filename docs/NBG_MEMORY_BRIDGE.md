# NBG Physical-Memory Bridge v0.1

Status: **experimental / advisory / non-qualifying**

This bridge converts a completed PhiPie host-health episode journal record into the current NestedBubbleGear epistemic-memory envelope.

The source contract is pinned to:

- repository: `MichaelWave369/NestedBubbleGear`
- schema: `schemas/epistemic-memory.schema.json`
- schema version: `NBG_EPISTEMIC_1`
- schema blob SHA: `56d39e4c9823ce4186affb5ea3a0df8783675121`

## Why the episode enters NBG as INFERRED

The underlying telemetry was observed, but a health episode is a deterministic interpretation over multiple observations:

```text
observed telemetry
      |
      v
baseline comparison
      |
      v
watch / notable / stable classifications
      |
      v
episode boundary + recovery decision
```

That means the NBG memory is labeled `INFERRED`, with the PhiPie journal record attached as `OBSERVATION` evidence. The bridge does not launder a derived episode into raw observed fact.

## Authority mapping

The emitted NBG authority envelope is fixed to:

```text
retainable      = true
reasoningUsable = true
actionAuthorized = false
```

The content also carries explicit semantic boundaries:

```text
episodeIsFault          = false
stableMeansSafe         = false
actionAuthorityGranted  = false
```

So a PhiBot may remember and reason from the episode, but the memory itself never authorizes physical action.

## Time mapping

PhiPie health episodes currently have sequence positions, not qualified wall-clock valid time. The bridge therefore emits:

```json
{
  "basis": "phipie_host_sequence",
  "startSequence": 4,
  "endSequence": 8
}
```

as `validTime` rather than inventing timestamps.

`knownTime` is optional and must be provided by the caller if a qualified known-time value exists.

## Fingerprint compatibility

NestedBubbleGear currently fingerprints epistemic memories with browser-side FNV-1a 32 over stable JSON using JavaScript UTF-16 code units.

The PhiPie bridge implements the same UTF-16 behavior and carries test vectors for ASCII and Unicode text. This is compatibility with the current NBG record format, not a cryptographic-security claim.

The PhiPie episode journal remains SHA-256 chained. The bridge verifies the source journal record hash before producing NBG memory.

## Memory flow

```text
PhiPie read-only telemetry
        |
        v
health baseline + drift
        |
        v
completed host-health episode
        |
        v
SHA-256 episode journal record
        |
        v
NBG bridge
        |
        v
NBG_EPISTEMIC_1 memory
  origin = INFERRED
  role = evidence
  actionAuthorized = false
```

## Acceptance signals

CI proves that:

1. the bridge emits the required `NBG_EPISTEMIC_1` structure;
2. NBG-compatible FNV fingerprints match reference vectors, including Unicode;
3. source journal tampering is refused;
4. episode/envelope identity mismatch is refused;
5. NBG memory tampering breaks record validation;
6. confidence remains bounded to `[0, 1]`;
7. action authority remains false;
8. the bridge pins the exact NBG schema blob used for compatibility.

## Non-claims

```text
NBG-compatible record != NBG repository integration
INFERRED != OBSERVED
confidence != verification
memory != fact
memory != actuator authority
FNV fingerprint != cryptographic integrity
bridge pass != hardware qualification
```

PHIPIE-03 remains the active Raspberry Pi 5 hardware field-candidate rung.
