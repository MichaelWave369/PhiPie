"""Field-probe evidence binding CLI. No network actions or hardware writes.

python -m trailcore.probe_bundle_cli manifest --output /private/manifest-v2.json
python -m trailcore.probe_bundle_cli inspect --witness /private/trial.json \
    --manifest /private/manifest-v2.json --evidence-dir /private/artifacts \
    --output /private/eight-file-assessment.json
"""
from __future__ import annotations
import argparse
import json
import sys
from .probe_bundle import probe_manifest_template, verify_probe_bundle
from .two_node_pilot import read_packet_file, write_private_json


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    subs = p.add_subparsers(dest="operation", required=True)
    m = subs.add_parser("manifest", help="New private eight-slot manifest")
    m.add_argument("--output", required=True)
    a = subs.add_parser("inspect", help="Verify eight private field files, locally")
    for flag in ("witness", "manifest", "evidence-dir", "output"):
        a.add_argument("--" + flag, required=True)
    args = p.parse_args(argv)
    try:
        if args.operation == "manifest":
            write_private_json(args.output, probe_manifest_template())
            print(json.dumps({"status": "PRIVATE_PROBE_MANIFEST_CREATED",
                              "hardware_qualified": False}))
            return 0
        report = verify_probe_bundle(
            read_packet_file(args.witness),
            read_packet_file(args.manifest),
            args.evidence_dir,
        )
        write_private_json(args.output, report)
        print(json.dumps({"status": report["status"], "reasons": report["reasons"],
                          "hardware_qualified": False}))
        return 0 if report["status"] == "LOCAL_PROBE_EVIDENCE_MATCH" else 2
    except (OSError, ValueError, TypeError, UnicodeError, OverflowError):
        print(json.dumps({"status": "HOLD", "reason": "PRIVATE_EVIDENCE_FAILURE",
                          "hardware_qualified": False}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
