"""Operator-approved PhiPie Trail 3-second TCP capacity observation.

Requires an existing, separately operated iperf3 server at an authorized
private IPv4 target. Sends actual traffic at an application pacing target
of 1 Mbps (SOFT, NOT a strict network cap). Does not open or manage servers.

python -m trailcore.tcp_cli --target 192.168.1.20 --approve-tcp \
    --output "$HOME/trail-field/artifacts/tcp-observation.json"
"""
from __future__ import annotations
import argparse
import json
import sys
from .tcp_observer import observe_tcp
from .two_node_pilot import write_private_json


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target", required=True, help="Authorized private IPv4 only")
    p.add_argument("--approve-tcp", action="store_true",
                   help="Authorize one TCP throughput client test (generates traffic)")
    p.add_argument("--output", required=True, help="New private JSON path; no overwrite")
    a=p.parse_args(argv)
    try:
        if not a.approve_tcp:
            print(json.dumps({"status": "HOLD", "reason": "OPERATOR_APPROVAL_REQUIRED",
                              "traffic_generated": False, "hardware_qualified": False}))
            return 2
        report=observe_tcp(a.target, approved=True)
        if report["status"] != "LOCAL_TCP_OBSERVED":
            print(json.dumps({"status": "HOLD", "reason": report["reason"],
                              "hardware_qualified": False}))
            return 2
        write_private_json(a.output, report)
        print(json.dumps({"status": "LOCAL_TCP_FILE_WRITTEN",
                          "hardware_qualified": False, "traffic_generated": True,
                          "network_change_authorized": False}))
        return 0
    except (OSError, ValueError, TypeError, UnicodeError, OverflowError):
        print(json.dumps({"status": "HOLD", "reason": "PRIVATE_OUTPUT_FAILURE",
                          "hardware_qualified": False}))
        return 2


if __name__=="__main__":
    sys.exit(main())
