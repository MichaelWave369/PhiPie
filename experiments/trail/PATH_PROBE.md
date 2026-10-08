# ΦTrail PR #18: Bounded ICMP probe → privately bound field evidence

**Status: experimental, operator-approved, non-qualifying.** This rung
closes a narrow gap: PR #17 could check that a manually written path summary
matched its file hash, but it had no connection to actual parsed ping output.

Here an operator may explicitly ask the existing Linux `ping` observer to
send **exactly three** packets to an authorized private/link-local IPv4
address via a chosen observed Wi-Fi interface. A strict eight-file local
review checks that the private parsed probe output and normalized path
summary contain identical measured packet loss and average RTT.

This is **not** a mesh controller, a throughput benchmark, device attestation,
proof of independent route, or credential/permission system.

## Optional, bounded active observation

Run on an owned, authorized Linux/PhiPie node where `iw` and `ping` are
installed, and only after confirming the target is part of your local
network. **It generates ICMP traffic.** Nothing runs in the background:

```bash
umask 077
mkdir -p "$HOME/trail-field/artifacts"
chmod 700 "$HOME/trail-field/artifacts"
cd experiments/trail
python -m trailcore.path_probe_cli \
  --interface wlan0 --target 192.168.1.1 --approve-probe \
  --probe-out "$HOME/trail-field/artifacts/icmp-probe.json" \
  --path-out "$HOME/trail-field/artifacts/path-observation.json"
```

This reuses #14's command allowlist:
`ping -n -I wlan0 -c 3 -W 1 192.168.1.1` with a six-second process
timeout. No shell injection, router configuration, retries in the
background, public-IP probes, or autonomous rover movement.

If link/interface support is missing or even one required metric is
unavailable, the collector returns HOLD and does not write a positive
record. The two outputs are exclusive, owner-only JSON files, **not** an
atomic pair: an interrupted write leaves artifacts for the operator to
inspect and should never be auto-retried under the same filename.

- `icmp-probe.json`: bounded parsed output from #14, its checksum, the
  operator-authorized source marker, target private IP and interface name.
  **Sensitive to infrastructure layout; keep it private.**
- `path-observation.json`: legacy #17 schema
  `phipie-trail-path-evidence/v0.1`. `kind=ICMP`,
  `throughput_mbps=null`, and `evidence_origin` retains the existing
  `OPERATOR_RECORDED_INDEPENDENT` label for backwards compatibility.
  The new eight-file verification is what specifically binds this summary
  to the bounded parsed output.

Neither file proves that the operating system provided genuine physical
measurements. The program parses local tool output, which an untrusted
host or test double could fabricate.

## Bind the eighth evidence file

PR #17's seven-file manifest and `evidence_cli` remain unchanged.

For a **new** two-node trial, use an eight-file manifest:

```bash
python -m trailcore.probe_bundle_cli manifest \
  --output "$HOME/trail-field/manifest-v2.json"
```

It includes the original seven slots plus an eighth
`icmp_probe` → `icmp-probe.json`.

Use #16's protected `trial.json` and #15's signed packet and receipt,
plus host/radio evidence from **both physical nodes**. Set
`trial.path_test.kind=ICMP`, copy the measured loss and average RTT from
the **normalized path file**, and set its `evidence_sha256` to
`sha256sum path-observation.json` of the exact file bytes.

Review the eight-file bundle:

```bash
python -m trailcore.probe_bundle_cli inspect \
  --witness "$HOME/trail-field/trial.json" \
  --manifest "$HOME/trail-field/manifest-v2.json" \
  --evidence-dir "$HOME/trail-field/artifacts" \
  --output "$HOME/trail-field/probe-assessment.json"
```

The inspector first verifies all original #17 seven-file references,
then opens `icmp-probe.json` and the normalized path file from the
private directory (no symlinks, traversal or loose file permissions).
It validates the reporter contract, source marker, zero-authority flags,
inner checksum, exact 3-packet accounting, plausible packet loss, private
target and metrics cross-consistency. Missing/replaced/unsafe data → HOLD.

A positive result is named `LOCAL_PROBE_EVIDENCE_MATCH`, not
`HARDWARE_QUALIFIED`. This asserts only that the local files are
internally consistent. It cannot replay raw packet captures, prove
independent peer identity, route availability or the honesty of the
underlying ping output.

**All authorization and qualification flags stay false.**
The receiver's #15 HMAC key is not available to this binder, and a
checksum does not authenticate the sender. No NBG, SOMA, Infinite Porch
or live Vessie runtime wiring is added.

## Reproducible software tests

```bash
cd experiments/trail
python -m unittest discover -s tests -v
python -m trailcore.path_probe_cli --help
python -m trailcore.probe_bundle_cli --help
```

GitHub CI uses **fake** `iw` and `ping` responses. Passing CI is not
physical Pi validation or proof of Internet connectivity.

## What is still missing

A real two-Pi operator-supervised test, independently preserved raw
ping/driver/clock observations, measured TCP/UDP throughput with a
separately scoped test harness, validated multi-hop Wi-Fi transport,
secure per-device identity with durable anti-replay, and authorized
field-site deployment conditions.

**A ping is a measurement, not a miracle.**
