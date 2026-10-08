"""Operator CLI for read-only PhiPie radio observations; nothing auto-starts.

Usage:
  python -m trailcore.radio_cli --list
  python -m trailcore.radio_cli --interface wlan0
  python -m trailcore.radio_cli --interface wlan0 --approve-probe --probe-target 192.168.1.1
  python -m trailcore.radio_cli --interface wlan0 --draft-site lab --draft-node relay-a --draft-peer base --draft-seq 1

'--draft' fields create only an UNSIGNED candidate; no device identity
has been authenticated and no live SOMA/Porch transport is used.
"""
from __future__ import annotations

import argparse
import json
import sys

from .linux_radio import list_radios, make_soma_radio_unsigned, observe_ping, observe_radio


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="List iw-discovered interface names, no identifiers")
    parser.add_argument("--interface", help="Known Linux wireless interface, e.g. wlan0")
    parser.add_argument("--approve-probe", action="store_true", help="Explicitly authorize one bounded ICMP probe")
    parser.add_argument("--probe-target", help="Private or link-local IPv4 target")
    parser.add_argument("--draft-site", help="Operator-supplied SOMA site name (unsigned only)")
    parser.add_argument("--draft-node", help="Operator-supplied SOMA node name (unsigned only)")
    parser.add_argument("--draft-peer", help="Operator-supplied peer alias (unverified)")
    parser.add_argument("--draft-seq", type=int, help="SOMA lab-only sequence (unsigned only)")
    parser.add_argument("--draft-id", default="radio-observation-1", help="SOMA draft observation ID")
    args = parser.parse_args(argv)
    if args.list and (args.interface or args.approve_probe or args.probe_target):
        parser.error("--list cannot be combined with interface or probe options")
    if bool(args.probe_target) != bool(args.approve_probe):
        parser.error("--probe-target requires --approve-probe and vice versa")
    if not args.list and not args.interface:
        parser.error("select --list or --interface")
    draft_args = (args.draft_site, args.draft_node, args.draft_peer, args.draft_seq)
    if any(v is not None for v in draft_args) and not all(v is not None for v in draft_args):
        parser.error("all --draft-site, --draft-node, --draft-peer, --draft-seq are required")
    if args.list and any(v is not None for v in draft_args):
        parser.error("draft requires an interface observation")
    if args.list:
        out = list_radios()
        out["mode"] = "READONLY_LOCAL_OBSERVER"
    else:
        report = observe_radio(args.interface)
        out = {"radio": report, "mode": "READONLY_LOCAL_OBSERVER"}
        if args.probe_target:
            out["ping"] = observe_ping(args.probe_target, args.interface, approved=True)
        if all(v is not None for v in draft_args):
            out["soma_unsigned_draft"] = make_soma_radio_unsigned(
                report, site_id=args.draft_site, node_id=args.draft_node,
                peer_id=args.draft_peer, sequence=args.draft_seq,
                observation_id=args.draft_id,
            )
    print(json.dumps(out, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
