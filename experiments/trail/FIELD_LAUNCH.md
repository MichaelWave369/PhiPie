# ΦTrail PR #20: First Physical-Pi Field Launch Kit v0.1

**Scope: read-only preflight and one local capture per node.**
**No actual Pi was exercised by GitHub CI. All hardware qualification remains pending.**

This rung makes the *first physical two-Pi trial easier to start* without
creating an unreviewed network manager. It is a wrapper around #14's
read-only Linux `iw` radio observer and #16's privacy-limited host
snapshot, not a replacement for the independent #15–#19 security
and link-test qualification steps.

## 1. Prerequisites

On **two separate, operator-owned** Raspberry Pi 5 or Compute Module 5
Linux boards, check that the OS is already booted and the radios are
configured and connected through your authorized network by normal
operator provisioning. The field launcher does **not** configure Wi-Fi,
install packages, start servers, discover trusted peers or deploy relays.

Use Python 3.10+, `iw`, and an existing wireless interface (e.g. `wlan0`).
The optional `ping` and `iperf3` tools are listed as present/missing
but are **never launched** by the field kit.

No passwords, SSIDs, BSSIDs, MAC addresses, GPS, serials, MAC-derived
device identities, raw command output, or keys appear in saved records.

## 2. Check each board without transmitting

On sender A and receiver B independently:

```bash
cd experiments/trail
python -m trailcore.field_launch_cli doctor --interface wlan0
```

The result is `READY_FOR_READONLY_CAPTURE` or `HOLD`, with reasons
such as `IW_TOOL_MISSING`, `WIRELESS_INTERFACE_NOT_DISCOVERED`,
`PI_FAMILY_NOT_REPORTED`, or `LINUX_REQUIRED`.

**A successful doctor is only prerequisite discovery.** It reads
coarse locally-reported Pi model/kernel information and calls
`iw dev`, without probing any remote host or asserting site access.
An untrusted OS can spoof those details.

## 3. Capture once on each Pi

Choose a **new** session directory each time. No overwrite or
auto-retry is allowed; if interrupted, inspect the partial folder
and choose a new session path.

Sender A:

```bash
umask 077
mkdir -p "$HOME/trail-field"
chmod 700 "$HOME/trail-field"
cd experiments/trail
python -m trailcore.field_launch_cli collect \
  --interface wlan0 --role sender --node relay-a --test-id trial-001 \
  --session-dir "$HOME/trail-field/sender-001"
```

Receiver B:

```bash
umask 077
mkdir -p "$HOME/trail-field"
chmod 700 "$HOME/trail-field"
cd experiments/trail
python -m trailcore.field_launch_cli collect \
  --interface wlan0 --role receiver --node base-b --test-id trial-001 \
  --session-dir "$HOME/trail-field/receiver-001"
```

Each device creates exactly three owner-only files:

- `host.json`: coarse local hardware/OS report with embedded checksum.
- `radio.json`: read-only `iw` link report and checksum, or bounded
  HOLD/PARTIAL with missing metrics preserved as unknown.
- `session.json`: role/alias/test ID, checksum references, and
  explicit zero-authority/unattested/unqualified status.

If Wi-Fi retry counters are absent or the interface is disconnected,
the collector preserves **PARTIAL or HOLD** evidence rather than claiming
that zeros or synthetic values were physically measured.

These are two **independent** local reports. They do not establish
that the Pis have communicated, that either board is authenticated,
or that they are connected by a routed/multi-hop PhiPie service.

## 4. Continue the separate, operator-supervised tests

The field kit deliberately does not launch any other test:

- Use [two-node HMAC lab evidence](TWO_NODE_PILOT.md) to send a bounded
  signed packet via your own authorized secure *manual* channel.
- Use [the optional bounded ICMP observation](PATH_PROBE.md) only with
  deliberate approval on a private target.
- Use [the optional TCP capacity observer](TCP_EVIDENCE.md) only with
  deliberate approval and a separately operated, authorized
  `iperf3` server. Its 1 Mbps application pacing target is **not**
  guaranteed as a hard cap and it does **not** bind to a specific radio.
- Use the [field witness](FIELD_WITNESS.md) and
  [private evidence binder](EVIDENCE_BINDING.md) to review actual
  protected files. Transfer records using an independently approved,
  authenticated channel. Keep private infrastructure information and
  HMAC secrets off public GitHub.

You can use the per-node `host.json` and `radio.json` as the host and
radio evidence inputs in the existing protected field artifact set,
but operator site permission, clock agreement, physical board separation,
boot identity, safety checks, signed packet replay and real path
measurements **must still be independently witnessed**. A report hash is
not proof of device identity.

## 5. Refusal and non-claims

- No automatic network traffic: no ping, iperf3, tcp server,
  wireless scanning, SSID association or route changes.
- No unattended field service or physical Pi boot qualification.
- No identity attestation, TLS transport, durable multi-node consensus,
  automatic NBG/Infinite Porch/SOMA runtime integration or robot motion.
- Local checksums are not cryptographic device signatures.
- A single local report cannot qualify a two-node or multi-hop system.
- No emergency coverage claim or authorization to deploy on public land.

**CAPABILITY != AUTHORITY. READY_FOR_READONLY_CAPTURE != FIELD_PASS.**

## Automated checks

```bash
cd experiments/trail
python -m unittest discover -s tests -v
python -m trailcore.field_launch_cli --help
```

All CI observers use mocked Linux command output and fake Pi model
strings. A clean CI result supports only parser/capture/refusal behavior,
**not physical hardware readiness**.
