# ΦTrail Two-Node Evidence Pilot v0.1

**Status: EXPERIMENTAL / MANUAL FILE HANDOFF / READ-ONLY / NOT PHYSICALLY QUALIFIED.**

This pilot allows an operator to collect the existing read-only Linux `iw`
radio evidence on node A, create a narrowly scoped `sense.radio` SOMA v0.1
packet signed with a **pre-shared laboratory HMAC key**, manually transfer the
private JSON file to node B over a separately trusted channel, and verify it
against a **durable SQLite replay ledger**. It returns an advisory-only
ObservationReceipt on acceptance.

There is **no automatic radio network, router/AP configuration, Porch transport,
daemon, robotic drive, relay dispenser, NBG admission, or SPV live wiring**.

## Requirements

- Two Linux/Raspberry Pi hosts with Python 3.10+.
- `iw` installed on sender A and a connected Linux Wi-Fi interface.
- A driver reporting valid RSSI plus one-peer TX packet/retry counters over
  two samples. If retries are unsupported or traffic is idle, collect
  **refuses** rather than inventing metric values.
- Owner-only directory for key, packet and replay ledger; space for SQLite.
- A separately trusted means to transfer one key during lab setup and to
  transfer signed evidence each time. **This repository supplies no transfer
  protocol, mutual TLS, SSH setup, or remote access privileges.**
- Both nodes have independently synchronized system clocks. The existing
  `SomaIntake` freshness window is 90 seconds, so manual transfer can expire.

## Lab setup (explicit, one-time)

On **sender A** (use your own protected directory):

```bash
umask 077
mkdir -p "$HOME/trail-lab"
chmod 700 "$HOME/trail-lab"
cd experiments/trail
python -m trailcore.two_node_cli keygen --key-file "$HOME/trail-lab/site-key.hex"
```

Transfer that key ONCE to **receiver B** using your own secure, already
authorized channel. Do **not** publish it, paste it into chat, put it in
shell arguments, commit it to GitHub, or reuse any test fixture key.
Protect the copied file with mode `0600`. A stolen key can forge observations.

On receiver B:

```bash
umask 077
mkdir -p "$HOME/trail-lab"
chmod 700 "$HOME/trail-lab"
chmod 600 "$HOME/trail-lab/site-key.hex"
cd experiments/trail
python -m trailcore.two_node_cli init-ledger \
  --replay-db "$HOME/trail-lab/replay.sqlite"
```

The ledger is **explicitly initialized** using exclusive file creation.
The verifier refuses a missing, malformed or group/world-readable database
rather than silently creating a new empty replay history.

## Capture on sender A

```bash
cd experiments/trail
python -m trailcore.two_node_cli collect \
  --interface wlan0 --site-id test-camp --node-id relay-a \
  --peer-id gateway --key-id relay-a-key \
  --key-file "$HOME/trail-lab/site-key.hex" \
  --sequence 1 --output "$HOME/trail-lab/radio-0001.json"
```

The operator supplies *site*, *node*, *peer alias*, *key ID* and **strictly
increasing sequence**. They are NOT verified sensor identity or radio peer
attestations. Save the last sequence outside the device's volatile memory;
lost sender sequence state requires a human key/ledger recovery review.
The signed packet has a random observation ID and is mode 0600.

If `iw` cannot provide required evidence, the operation returns **HOLD**
and writes no signed packet. All link metrics are bounded and zero-authority.

**Do not mistake TX PHY bitrate for actual measured throughput.**
No packet transport is implemented here, and this does not produce
`sense.network.observed_mbps`.

## Verify on receiver B

Transfer `radio-0001.json` securely to the receiver's protected directory
and set permissions to `0600`. Then:

```bash
cd experiments/trail
python -m trailcore.two_node_cli receive \
  --input "$HOME/trail-lab/radio-0001.json" \
  --site-id test-camp --node-id relay-a --key-id relay-a-key \
  --key-file "$HOME/trail-lab/site-key.hex" \
  --replay-db "$HOME/trail-lab/replay.sqlite" \
  --receipt-out "$HOME/trail-lab/receipt-0001.json"
```

Only matching site/node/key binding, exact payload schema, timestamp freshness,
HMAC and previously unseen **monotonic** sequence/observation ID can pass.
On acceptance the ledger commits the sequence to SQLite and emits a read-only
receipt; a repeat `receive` on the same packet returns **HOLD** even after
a Python process restart. Full/damaged/locked SQLite ledger also blocks
admission rather than silently falling back to volatile memory.

The receiver does **not** automatically send receipts or evidence to
Infinite Porch, NBG, BrainC or SuperPhiVessel.

## Critical security and evidence limitations

- **HMAC is not an attested physical device identity.** Both sender and
  receiver know the same symmetric key; either can forge messages. It does
  not prove `iw` faithfully measured the claimed peer.
- **No secure transport is included.** Protect file transfer separately
  and minimize propagation of location/peer identifiers.
- **SQLite durability is not tamper-proof storage.** Deletion, restoring
  an old DB backup, cloned key + database images, storage rollbacks, and
  malicious local root processes can defeat the anti-replay guarantee.
  Recovery must be handled through a later governed rekey/epoch protocol.
- **Sequence is operator-managed, not crash-consistent on sender.**
  It must monotonically increase; never reset to 1 with the same key.
- **Clock correctness is externally assumed.** 90-second freshness can
  reject honest delayed transfers and cannot by itself prove clock quality.
- **HMAC uses Python-specific canonical JSON**, not a standardized cross-
  language signing format; do not assert third-party interoperability.
- A valid packet remains only an **observation claim**, not proven mesh
  availability, end-to-end data transport, actual network capacity, consent,
  authorization to configure anything, or a safety-critical link.

All zero-authority flags inherited from SOMA #13 remain false.
No Pi 5 field boot or hardware validation is claimed.

## Acceptance tests

```bash
cd experiments/trail
python -m unittest discover -s tests -v
python -m trailcore.two_node_cli --help
```

GitHub CI uses a fake `iw` runner, temp owner-only keys, and temp SQLite DBs.
It tests modified payloads, mismatched bindings, duplicate keys, missing
or corrupt ledger, cold-restart replay refusal and simultaneous acceptance.

**A green CI check means only the offline contract passed.**
