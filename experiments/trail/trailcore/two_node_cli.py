"""Offline operator-mediated ΦTrail two-node pilot, no transport or hardware writes.

Examples:
    python -m trailcore.two_node_cli keygen --key-file /secure/trail.key
    python -m trailcore.two_node_cli init-ledger --replay-db /secure/receiver.sqlite
    python -m trailcore.two_node_cli collect --interface wlan0 --site-id camp --node-id relay-a \
        --peer-id gateway --key-id relay-a-key --key-file /secure/trail.key \
        --sequence 1 --output /secure/radio-1.json
    python -m trailcore.two_node_cli receive --site-id camp --node-id relay-a \
        --key-id relay-a-key --key-file /secure/trail.key \
        --replay-db /secure/receiver.sqlite --input /secure/radio-1.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from .durable_replay import DurableReplayWindow
from .two_node_pilot import (
    collect_signed_radio, create_lab_key, read_packet_file,
    receive_signed_radio, write_private_json,
)


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    subs = p.add_subparsers(dest="operation", required=True)
    key = subs.add_parser("keygen", help="Create local random 0600 lab key, no overwrite")
    key.add_argument("--key-file", required=True)
    init = subs.add_parser("init-ledger", help="Explicitly create new local SQLite anti-replay DB")
    init.add_argument("--replay-db", required=True)
    collect = subs.add_parser("collect", help="Observe local link and create signed private packet")
    collect.add_argument("--interface", required=True)
    collect.add_argument("--peer-id", required=True, help="Manual alias, not hardware attestation")
    collect.add_argument("--sequence", type=int, required=True, help="Persistent operator-assigned increasing sequence")
    collect.add_argument("--output", required=True, help="New private packet JSON path; no overwrite")
    receive = subs.add_parser("receive", help="Verify signed packet with durable replay DB")
    receive.add_argument("--replay-db", required=True)
    receive.add_argument("--input", required=True, help="Manual secure-file-transfer input")
    receive.add_argument("--receipt-out", help="Optional new private receipt file")
    for sp in (collect, receive):
        sp.add_argument("--site-id", required=True)
        sp.add_argument("--node-id", required=True)
        sp.add_argument("--key-id", required=True)
        sp.add_argument("--key-file", required=True, help="0600 file path only, never secret in argv")
    return p


def main(argv=None) -> int:
    p = _parser()
    args = p.parse_args(argv)
    try:
        if args.operation == "keygen":
            create_lab_key(args.key_file)
            print(json.dumps({"status": "CREATED", "mode": "LOCAL_LAB_KEY_ONLY"}))
            return 0
        if args.operation == "init-ledger":
            DurableReplayWindow.initialize(args.replay_db)
            # Verify schema and local file permissions immediately.
            DurableReplayWindow(args.replay_db)
            print(json.dumps({"status": "INITIALIZED", "mode": "LOCAL_SQLITE_REPLAY_ONLY"}))
            return 0
        if args.operation == "collect":
            packet = collect_signed_radio(
                interface=args.interface, site_id=args.site_id, node_id=args.node_id,
                peer_id=args.peer_id, sequence=args.sequence, key_id=args.key_id,
                key_file=args.key_file,
            )
            if packet is None:
                print(json.dumps({"status": "HOLD", "reason": "INCOMPLETE_RADIO_EVIDENCE",
                                  "packet_written": False}))
                return 2
            write_private_json(args.output, packet)
            print(json.dumps({"status": "PACKET_WRITTEN",
                              "mode": "MANUAL_FILE_HANDOFF_NOT_FIELD_AUTHENTICATION",
                              "packet_written": True}))
            return 0
        if args.operation == "receive":
            packet = read_packet_file(args.input)
            result = receive_signed_radio(
                packet, site_id=args.site_id, node_id=args.node_id,
                key_id=args.key_id, key_file=args.key_file,
                replay_db=args.replay_db, now_s=time.time(),
            )
            if result["status"] != "ACCEPTED_ADVISORY_ONLY":
                print(json.dumps({"status": "HOLD", "reason": result["reason"]}))
                return 2
            if args.receipt_out:
                write_private_json(args.receipt_out, result)
            print(json.dumps({"status": "ACCEPTED_ADVISORY_ONLY",
                              "receipt_sha256": result["receipt"]["receipt_sha256"],
                              "hardware_authority_granted": False,
                              "network_transport_established": False}))
            return 0
    except (OSError, ValueError, TypeError, RuntimeError, UnicodeError):
        # Fail without exposing sensitive key/file contents or OS command stdout.
        print(json.dumps({"status": "HOLD", "reason": "LOCAL_IO_OR_VALIDATION_FAILURE"}))
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
