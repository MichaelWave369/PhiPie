# ΦTrail Linux Physical Radio Observer v0.1

**Status:** EXPERIMENTAL / READ-ONLY / HARDWARE UNQUALIFIED / NOT A MESH DRIVER

This is the first OS-facing measurement adapter in PhiPie Trail. It uses
Linux `iw` to **observe** available Wi-Fi interfaces, link RSSI, current
TX PHY rate and channel frequency. If a *single station* exposes two usable
transmit-packet and retry-counter snapshots, it estimates an attempted-
transmission retry fraction. Some drivers do **not** expose station counters
on a managed interface; then `retry_pct=null` and the report stays PARTIAL.

It never pretends that PHY rate equals user payload throughput.
It never treats a link RSSI/PHY bitrate as end-to-end connectivity.

## Run on a Raspberry Pi / Linux with `iw` installed

```bash
cd experiments/trail
python -m trailcore.radio_cli --list
python -m trailcore.radio_cli --interface wlan0
```

All requests are synchronous; there is no service, background watcher, automatic
execution, radio scanning, association, interface write or configuration change.

On failure or unsupported hardware, the observer returns HOLD or PARTIAL with
bounded reasons. Never synthesize data to make an organ packet validate.

## Optional bounded active network probe

**This makes real ICMP packets, and is OFF by default.**

Only run on your own/authorized network and target:

```bash
python -m trailcore.radio_cli --interface wlan0 --approve-probe --probe-target 192.168.1.1
```

The only allowed probe is a single system `ping -n -I <interface> -c 3 -W 1
<private-or-link-local-IPv4>` invocation with a six-second subprocess timeout.
Its arguments are explicitly validated; it uses no shell and cannot target a
public IP. An operator's CLI approval is **not** an authentication or site
authorization protocol. It can still produce traffic or fail due to operating
system capabilities/firewall rules.

If results exist, the output includes measured ICMP average RTT and packet
loss. These are *one target's ICMP results*, not evidence of whole-route
availability, meaningful traffic priority, path throughput, or emergency service.
Even a successful ping leaves `observed_mbps=null`: ICMP cannot supply the
`sense.network.observed_mbps` SOMA requirement. There is consequently
**no automatic `sense.network` packet** from this probe.

## SOMA radio draft: strict evidence only

For a complete radio observation only:

```bash
python -m trailcore.radio_cli --interface wlan0 \
  --draft-site lab --draft-node relay-a --draft-peer base --draft-seq 1
```

This emits an **UNSIGNED candidate**, only if both RSSI and estimated retries
are actually observed. `peer_id` is a human-provided non-secret alias, *not*
a verified BSSID/device identity. No key is provisioned; no HMAC is performed;
the output is refused by the existing `SomaIntake` unless separately signed
and independently admitted by a trusted host.

This is deliberate. PR #13's HMAC verifier is laboratory-only with a volatile
replay ledger, and must not become an unattended field trust boundary.
The offline test harness can produce a synthetic lab signature and demonstrate
the `sense.radio` → SOMA `ObservationReceipt` acceptance, but that does not
qualify any hardware identity, radio measurement or distributed transport.

## Data contract and non-claims

Output `phipie-trail-linux-radio-observer/v0.1`:

- `status`: HOLD, PARTIAL, or COMPLETE for passive radio,
  OBSERVED_ADVISORY_ONLY for explicitly approved ping.
- `metrics.rssi_dbm`: received signal reading from `iw dev IFACE link`.
- `metrics.tx_phy_mbps`: current PHY TX link rate, **not throughput**.
- `metrics.frequency_mhz`: channel frequency, when reported.
- `metrics.retry_pct`: estimated retry attempt fraction over two station
  snapshots, computed as delta(retries) / (delta(tx packets)+delta(retries)).
  This is a *heuristic*, not true retransmission probability or radio quality.
- `metrics.sample_count`: counted TX attempts over the counter-delta interval.
- `observed_at_s`: host wall-clock reading, **not a trusted timestamp**.
- `evidence_sha256`: local deterministic checksum, **not a signature**.
- `provenance`: observer name, measurement method and limitation markers.
- Authority fields **all false**.

Output never includes raw command output, SSIDs, BSSIDs, MAC addresses or raw
ping packet contents. The raw observations are ephemeral in process and no
files are automatically written. An operator who redirects JSON output to a
file is responsible for its storage and retention.

All compatibility/fail-closed behavior can be exercised on any machine with
Python 3.10+ using fake injected `iw`/`ping` command responses:

```bash
cd experiments/trail
python -m unittest discover -s tests -v
```

## Field qualification remaining

- Real-board Pi 5 test log: `iw` availability, driver/firmware, radio type,
  permissions, Linux distro, link mode and antenna identity.
- Repeated RSSI and counter snapshots under idle/load, and expected missing/
  reset/multi-station cases. Keep raw privileged capture **off public GitHub**.
- Independent end-to-end packet-path and throughput tests through *actual*
  multi-hop radios; strict identity, signed transport, durable anti-replay.
- Radio privacy/consent and compliance with location/land/radio regulations.
- Operator-approved Park Rover survey with independent safety controller.
- A separate promotion process for NBG/SuperPhiVessel, if ever pursued.

**No real radio was exercised in GitHub CI.** PHIPIE-03 remains field candidate.
Motor control, relay deployment, router changes and unrelated PhiOS runtimes
remain outside this module.
