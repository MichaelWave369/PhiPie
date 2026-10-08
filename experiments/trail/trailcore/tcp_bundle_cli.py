"""Local nine-file TCP/ICMP witness binding; never sends network traffic."""
from __future__ import annotations
import argparse
import json
import sys
from .tcp_bundle import tcp_manifest_template, verify_tcp_bundle
from .two_node_pilot import read_packet_file, write_private_json


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="operation",required=True)
    new=sub.add_parser("manifest")
    new.add_argument("--output",required=True)
    review=sub.add_parser("inspect")
    for name in ("witness","manifest","evidence-dir","output"):
        review.add_argument("--"+name,required=True)
    args=p.parse_args(argv)
    try:
        if args.operation=="manifest":
            write_private_json(args.output,tcp_manifest_template())
            print(json.dumps({"status":"PRIVATE_TCP_MANIFEST_CREATED","hardware_qualified":False}))
            return 0
        result=verify_tcp_bundle(
            read_packet_file(args.witness),read_packet_file(args.manifest),args.evidence_dir
        )
        write_private_json(args.output,result)
        print(json.dumps({"status":result["status"],"reasons":result["reasons"],
                          "hardware_qualified":False}))
        return 0 if result["status"]=="LOCAL_TCP_EVIDENCE_MATCH" else 2
    except (OSError,ValueError,TypeError,OverflowError,UnicodeError):
        print(json.dumps({"status":"HOLD","reason":"PRIVATE_TCP_EVIDENCE_FAILURE",
                          "hardware_qualified":False}))
        return 2


if __name__=="__main__":
    sys.exit(main())
