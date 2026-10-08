# ΦTrail PR #19: Bounded TCP capacity observation and nine-file evidence

**Status: EXPERIMENTAL / OPT-IN / ACTIVE NETWORK TEST / NOT FIELD QUALIFICATION**

Our radio observation (#14) reports Wi-Fi RSSI, PHY rate and retry estimates.
Our ping probe (#18) reports a few packet RTTs and packet loss. Neither can
measure application TCP data transfer capacity. This rung adds an
**operator-approved, single-client** `iperf3` test, then binds its parsed,
private result to the existing eight-file field record as a ninth artifact.

## What runs on the network

The source device needs `iperf3` installed and a **separately started,
operator-owned iperf3 server** at a permitted private IPv4 address. This
software **never** starts, manages, configures or exposes that server.

```bash
cd experiments/trail
umask 077
mkdir -p "$HOME/trail-field/artifacts"
chmod 700 "$HOME/trail-field/artifacts"
python -m trailcore.tcp_cli \
  --target 192.168.1.20 --approve-tcp \
  --output "$HOME/trail-field/artifacts/tcp-observation.json"
```

The only allowed subprocess is a *client*, equivalent to:

```text
iperf3 -4 -c 192.168.1.20 -p 5201 -t 3 -b 1M -P 1 -J
```

- `-b 1M`: **soft target bitrate**, not a hard guaranteed bandwidth cap.
  Drivers, kernel buffers, iperf3 versions, and traffic bursts may differ.
- `-t 3`: three-second intended test duration, with an **eight-second**
  subprocess timeout. A slow/dropped connection returns HOLD.
- `-P 1`: one stream only, never flood multiple peers.
- IPv4 target must be private/link-local, never a public address, hostname,
  loopback address, or shell expression.
- The command **does not bind to a specific Wi-Fi interface**. The host's
  routing table selects the route, so this is *not* evidence that a PhiPie
  relay transported the data, nor evidence of a multi-hop path.
- If `iperf3` is missing, server unreachable, output inconsistent, or rate
  outside bounds, the test returns HOLD and no positive evidence is emitted.

The observer saves only selected metrics (received/sent data bytes,
throughput, duration, retransmits) and limitations. The raw iperf3
output is not published, and CLI stdout omits the target IP. As in earlier
rungs, keep the private file in an owner-only directory: it still includes
the private target address and is **not** suitable for public GitHub.

## Ninth file and backwards compatibility

Seven-file (#17) and eight-file (#18) inspectors remain unchanged. The
new **nine-file** checker adds a distinct `tcp_observation` slot to the
eight original slots. The path witness continues to describe the bounded
ICMP result. TCP capacity is a **separate** measurement, not a fabricated
replacement for ping throughput.

```bash
python -m trailcore.tcp_bundle_cli manifest \
  --output "$HOME/trail-field/tcp-manifest.json"
```

After independently collecting the other eight files under
`$HOME/trail-field/artifacts`, verify:

```bash
python -m trailcore.tcp_bundle_cli inspect \
  --witness "$HOME/trail-field/trial.json" \
  --manifest "$HOME/trail-field/tcp-manifest.json" \
  --evidence-dir "$HOME/trail-field/artifacts" \
  --output "$HOME/trail-field/tcp-assessment.json"
```

Verification first rechecks all eight previous files. For the ninth it
checks the strict TCP report, SHA-256, source and limitation labels,
private target, fixed port/test/pacing values, bounded byte count,
plausible durations, retransmit structure, and throughput arithmetic.
The result reveals **only** the numeric receiver throughput if all
nine files are internally consistent. It never reveals the private
target address or raw credentials.

`LOCAL_TCP_EVIDENCE_MATCH` means **local file consistency only**,
not authenticated remote host identity or physically qualified data
transfer. A compromised machine can fabricate an iperf3 JSON report.
The app is not a hardware attestation service.

## Negative controls / CI

```bash
python -m unittest discover -s tests -v
python -m trailcore.tcp_cli --help
python -m trailcore.tcp_bundle_cli --help
```

Tests replace the client with a fake runner: **CI sends no network
traffic** and does not run on a real Pi. The test suite refuses missing
operator approval, nonprivate targets, server failure, tampered fields,
fake hard-cap claims, unsafe files, and incongruent upstream ICMP evidence.

## Physical work remains

A supervised trial on **two actual owned Raspberry Pis** with an
independently authenticated endpoint, real routed-topology diagrams,
clock evidence, app throughput measurements and preserved raw logs.
Before claiming *wilderness service*, also validate terrain, relay
power and recovery, RF regulations/land access, independent emergency
communications, and realistic 2-/3-hop failure behavior.

**PHIPIE-03 remains a field candidate. An iperf3 number does not confer
hardware qualification, authority to change routing, or Rover motion.**
