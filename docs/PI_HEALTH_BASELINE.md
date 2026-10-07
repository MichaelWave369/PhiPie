# PhiPie Health Baseline + Drift v0.1

Status: **experimental / advisory / non-qualifying**

This slice sits above the merged Raspberry Pi read-only telemetry adapter.

Its job is to let a PhiPie learn a small, local, explainable baseline of its own observed operating pattern and compare later observations against that baseline.

It does **not** change Plane A safety state and it has **zero actuator authority**.

## Data path

~~~text
read-only Pi telemetry
        |
        v
baseline capture
        |
        v
median + robust spread
        |
        v
later read-only observation
        |
        v
stable / watch / notable
        |
        v
diagnostic receipt
~~~

This is engineering self-observation, not consciousness and not a safety controller.

## Baseline metrics

When available in at least the minimum sample count:

- CPU temperature;
- 1-minute load average;
- available-memory ratio;
- observed core voltage;
- count of interfaces with carrier.

The baseline also records which Raspberry Pi throttling flags were present during capture.

## Method

v0.1 deliberately uses a transparent deterministic heuristic:

- center = median;
- spread = median absolute deviation (MAD);
- scale = max(1.4826 × MAD, a small per-metric floor);
- drift score = (observed - median) / scale.

Classification:

~~~text
abs(score) < 3         -> stable
3 <= abs(score) < 6    -> watch
abs(score) >= 6        -> notable
~~~

A throttling flag that was not present in the baseline is classified as 'notable'.

These numbers are **diagnostic heuristics**, not certified thermal, electrical, or reliability limits.

## Identity binding

A baseline records the hashed board-serial and machine-ID fingerprints exposed by the read-only telemetry layer.

The builder refuses to mix samples from two known different identities.

A later identity mismatch causes drift scoring to be refused rather than quietly comparing one device to another.

If identity is unavailable, the report says so and remains observation-only.

## Why this stays outside Plane A

A learned baseline can accidentally learn a bad condition.

For example, a poorly cooled board could produce a very consistent high temperature. Consistency does not make the temperature safe.

Therefore:

~~~text
baseline normal != safe
drift notable != fault
drift stable != healthy
diagnostic score != actuator authority
~~~

Plane A keeps independent hard limits and deterministic safety logic.

## Capture on a Pi

From the repository root:

~~~bash
python -m runtime.physical_host.health_baseline capture --samples 5 --interval 2 --out phipie-baseline.json
~~~

Compare a later observation:

~~~bash
python -m runtime.physical_host.health_baseline check --baseline phipie-baseline.json --pretty
~~~

The generated baseline is local data. It should be reviewed before sharing because even hashed device fingerprints may be linkable across exported records.

## Acceptance signals

CI proves that:

1. too few observations cannot produce a baseline;
2. samples from different known device identities cannot be mixed;
3. small drift remains stable;
4. large thermal drift becomes notable;
5. new throttling flags become notable;
6. missing metrics remain missing rather than being fabricated;
7. an identity mismatch refuses drift scoring;
8. diagnostic observation does not change the physical-host safety state;
9. the observer has no actuator execution surface;
10. baseline serialization round-trips deterministically.

## Non-claims

~~~text
baseline learned != machine learning model
baseline normal != safe
notable drift != hardware fault
stable drift != hardware health certification
hashed identity != anonymous identity
diagnostic receipt != safety receipt
observer != Plane A
~~~

PHIPIE-03 remains the active Raspberry Pi 5 hardware field-candidate rung.
