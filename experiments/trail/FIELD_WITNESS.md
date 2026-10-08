# ΦTrail #16: Two-Pi Field Witness Kit v0.1

**State: EXPERIMENTAL / OPERATOR-SUPERVISED / NON-QUALIFYING**

This kit prepares a **real two-board observational session**, but neither a
successful GitHub test nor a filled-out form proves that two Pis actually
participated. PR #15's lab HMAC and SQLite replay proof remain advisory-only.
No equipment, motor, network link, or secure remote transport is configured.

## What this adds

- `field_cli host`: a coarse local Linux snapshot (reported Pi family,
  architecture, kernel major/minor, untrusted wall clock) without unique
  serial, MAC, BSSID, SSID, hostname, IP, coordinates, or secrets.
- `field_cli template`: strictly bounded two-node evidence form, **all
  confirmation fields false / all digests absent**.
- `field_cli assess`: validates the exact evidence structure, two distinct
  sender/receiver aliases, observation origins, boot witness assertions,
  handoff + durable replay refusal, tamper refusal, clock evidence,
  independent path test, and non-actuation testimony.
- `OPERATOR_REVIEW_CANDIDATE`: only when the supplied fields are complete,
  correct shape, and claim two observed physical Pi nodes. It is **not**
  physical qualification. It cannot prove assertions were truthful, verify
  digest contents, or certify a working mesh.
- `HOLD`: any incomplete/invalid/unsupported case, including simulation,
  stale/missing clocks, or ICMP claiming throughput.

The result always contains:

```json
{
  "hardware_physically_qualified": false,
  "mesh_transport_verified": false,
  "emergency_coverage_verified": false,
  "action_authorized": false,
  "network_change_authorized": false,
  "rover_motion_authorized": false,
  "soma_runtime_wired": false,
  "operator_claims_only": true
}
```

## Operator recipe (two owned Pi boards, permitted site)

On each device use its own protected directory. Do not publish raw captures:

```bash
umask 077
mkdir -p "$HOME/trail-field"
chmod 700 "$HOME/trail-field"
cd experiments/trail
python -m trailcore.field_cli host --output "$HOME/trail-field/host.json"
python -m trailcore.radio_cli --interface wlan0 > "$HOME/trail-field/radio.json"
```

The `host.json` file contains `snapshot_sha256`, a checksum over the
pre-checksum JSON record, and an **unverified reported platform family**.
The radio result includes an `evidence_sha256` checksum if observation
completed. Do not copy unverified values into field qualification claims.
Linux radio retries may be unavailable on real Pi drivers; unknown != zero.

Then follow [PR #15 two-node signed pilot](TWO_NODE_PILOT.md), using a distinct
random key in owner-only files, manually transferring one signed observation,
receiving it with protected SQLite state, checking an **actual subsequent
process invocation refuses replay**, and explicitly testing a tampered copy.
Keep packet/receipt filenames private. No manual step is automated here.

On a separately authorized local network, perform **independent** RTT/loss
tests (and a separate TCP throughput test only if supported). Keep the raw
test output privately and hash it. ICMP cannot establish throughput.
Observe clock agreement/offset using a trusted-for-your-site independent
method; do not invent synchronized clock evidence.

Create a template:

```bash
python -m trailcore.field_cli template \
  --output "$HOME/trail-field/trial.json"
```

**Manually** fill only bounded confirmation, mode and digest fields using
your real records. Keep `mode=OPERATOR_FIELD` only for an actual two-Pi
operator-observed trial. Use `LAB_SIMULATION` for fake fixtures and expect
HOLD, regardless of the other values.

Assess privately:

```bash
python -m trailcore.field_cli assess \
  --input "$HOME/trail-field/trial.json" \
  --output "$HOME/trail-field/assessment.json"
```

This writes a no-clobber, owner-only assessment. A duplicate path fails,
rather than overwriting evidence. A failed assessment is still written to
the private output for review (unless the input is unreadable). All outputs
are **inert**; this is not a router command.

## Evidence integrity and limitations

- `snapshot_sha256`, `evidence_sha256`, packet hashes and receipts are
  **operator-supplied** references; this kit does not open or cryptographically
  authenticate the referenced raw files. They are *not* device attestation.
- A malicious operator could fill the form with arbitrary valid hex digests.
  The report explicitly disclaims field qualification and cannot promote
  PHIPIE-03.
- The snapshot's `evidence_origin=LOCAL_LINUX` means locally read software
  reporting, not proven hardware authenticity or independently verified radio.
- A two-Pi evidence exercise is not 802.11s mesh, multi-hop routing, full
  Internet service, emergency coverage, or a PiOS boot qualification.
- Operator site consent, radio regulations, live environment constraints,
  secret handling, separate power/thermal evidence, and physical safety
  checks are still required. No unattended deployments in public woods.
- Memory and SOMA observations can inform analysis, never grant Rover motion.
- Test artifacts (especially operator notes and device reports) may reveal
  infrastructure; **do not upload field folders or secrets to a public repo**.

## CI / test signal

```bash
cd experiments/trail
python -m unittest discover -s tests -v
python -m trailcore.field_cli --help
```

Offline tests exercise a complete **synthetic** form (which may produce
an `OPERATOR_REVIEW_CANDIDATE` when falsely labeled OPERATOR_FIELD, proving
why operator assertions cannot be treated as hardware proof), refusals for
simulation and missing fields, and strict private-file writes.

**Next qualification is outside CI: run the procedure on two physical boards,
then have a human verify raw underlying evidence and consent before any
hardware-status claim.**
