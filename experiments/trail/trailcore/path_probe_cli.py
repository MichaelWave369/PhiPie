"""Explicitly approved bounded ICMP field-test collector for local PhiPie.

Example (generates exactly 3 ping packets when supported):
  python -m trailcore.path_probe_cli --interface wlan0 \
    --target 192.168.1.1 --approve-probe \
    --probe-out "$HOME/trail-field/artifacts/icmp-probe.json" \
    --path-out "$HOME/trail-field/artifacts/path-observation.json"

Outputs are private files. Stdout never contains IP, interface, raw output or
any credential. Tests/mock commands never create real packets.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .path_probe import collect_icmp_pair
from .two_node_pilot import write_private_json


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--interface", required=True)
    p.add_argument("--target", required=True, help="Operator-owned private/link-local IPv4 only")
    p.add_argument("--approve-probe", action="store_true",
                   help="Permission to send exactly three bounded ICMP packets")
    p.add_argument("--probe-out", required=True, help="New private original parsed probe file")
    p.add_argument("--path-out", required=True, help="New private normalized path-test record")
    args = p.parse_args(argv)
    try:
        a, b = Path(args.probe_out), Path(args.path_out)
        if a == b or a.exists() or b.exists() or a.is_symlink() or b.is_symlink():
            raise ValueError("unsafe or existing output path")
        if not a.parent.is_dir() or not b.parent.is_dir():
            raise ValueError("output parent must exist")
        # Must not perform even a three-packet probe without explicit approval.
        if not args.approve_probe:
            print(json.dumps({"status": "HOLD", "reason": "OPERATOR_PROBE_APPROVAL_REQUIRED",
                              "traffic_generated": False, "physical_hardware_qualified": False}))
            return 2
        pair = collect_icmp_pair(args.target, args.interface, approved=True)
        if pair["status"] != "LOCAL_PROBE_OBSERVED":
            print(json.dumps({"status": "HOLD", "reason": pair["reason"],
                              "physical_hardware_qualified": False}))
            return 2
        # No overwrite. These are two independent append-only files, not an
        # atomic transaction; an interrupted write requires operator inspection.
        write_private_json(a, pair["probe"])
        write_private_json(b, pair["path_record"])
        print(json.dumps({"status": "LOCAL_PROBE_FILES_WRITTEN",
                          "traffic_generated": True, "physical_hardware_qualified": False,
                          "network_change_authorized": False}))
        return 0
    except (ValueError, TypeError, OSError, OverflowError, UnicodeError):
        print(json.dumps({"status": "HOLD", "reason": "PROBE_OR_PRIVATE_OUTPUT_FAILURE",
                          "physical_hardware_qualified": False}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
