"""Operator PhiPie field kit: passive doctor and capture, no network probes.

From experiments/trail:
  python -m trailcore.field_launch_cli doctor --interface wlan0
  python -m trailcore.field_launch_cli collect --interface wlan0 \
    --role sender --node relay-a --test-id trial-001 \
    --session-dir "$HOME/trail-field/sender-001"

Run separately on sender and receiver. Never paste secrets into arguments.
No ping, iperf3, network setup, device writes or motor control.
"""
from __future__ import annotations
import argparse
import json
import sys

from .field_launch import collect_local, doctor


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    d = sub.add_parser("doctor", help="Read-only Pi/tool discovery, no saved files")
    d.add_argument("--interface", required=True)
    c = sub.add_parser("collect", help="One passive radio sample into fresh private session")
    c.add_argument("--interface", required=True)
    c.add_argument("--role", required=True, choices=("sender", "receiver"))
    c.add_argument("--node", required=True)
    c.add_argument("--test-id", required=True)
    c.add_argument("--session-dir", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            response = doctor(args.interface)
        else:
            response = collect_local(
                args.session_dir, role=args.role, node_id=args.node,
                test_id=args.test_id, interface=args.interface,
            )
        print(json.dumps(response, sort_keys=True, allow_nan=False))
        return 0 if response["status"] in {
            "READY_FOR_READONLY_CAPTURE", "LOCAL_CAPTURE_RECORDED"
        } else 2
    except (OSError, ValueError, TypeError, OverflowError, UnicodeError):
        print(json.dumps({
            "status": "HOLD", "reason": "LOCAL_PREFLIGHT_OR_CAPTURE_FAILURE",
            "physical_hardware_qualified": False,
        }))
        return 2


if __name__ == "__main__":
    sys.exit(main())
