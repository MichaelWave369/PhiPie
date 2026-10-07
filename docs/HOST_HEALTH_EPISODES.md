# Host Health Episodes v0.1

Status: **experimental / advisory / non-qualifying**

This slice converts repeated advisory drift reports into bounded longitudinal episodes.

It does not read hardware directly, change Plane A state, or grant execution authority. It consumes the diagnostic output already produced by the health-baseline layer.

## Why episodes

A single point can say that temperature or load moved away from a baseline. An episode preserves the sequence:

```text
stable
  -> watch
  -> notable
  -> recovery
  -> stable
```

That makes later memory useful without pretending every unusual reading is a fault.

## Episode rules

- `stable` by itself does not open an episode.
- `watch` or `notable` opens an episode.
- a later `notable` observation raises the episode peak severity.
- insufficient observations are retained as gaps and do not close an episode.
- recovery requires consecutive stable observations.
- a known identity mismatch aborts the active episode instead of mixing devices.

## Memory envelope

Completed episodes can be reduced to a neutral memory envelope containing:

- host identity fingerprints already produced by the telemetry layer;
- start and end sequence numbers;
- peak classification;
- metric names that entered watch/notable state;
- newly observed throttling flags;
- close reason;
- `suggested_memory_role = evidence`;
- `authority_effect = none`.

This envelope is intentionally shaped so a later NBG bridge can ingest episode evidence without importing PhiPie hardware logic into NBG.

## Local journal

The module also defines an append-only local episode journal with chained SHA-256 records. Only completed or aborted episodes may be written. The journal is evidence storage, not authorization.

## Non-claims

```text
episode != fault
episode peak != safety severity
recovery != certified health
journal != independent verification
memory envelope != authority
NBG-ready != NBG-integrated
```

PHIPIE-03 remains the active Raspberry Pi 5 hardware field-candidate rung.
