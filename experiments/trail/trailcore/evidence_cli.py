"""ΦTrail private-file evidence binding CLI. Local-only, non-qualifying.

python -m trailcore.evidence_cli manifest --output /private/manifest.json
python -m trailcore.evidence_cli inspect --witness /private/trial.json \
  --manifest /private/manifest.json --evidence-dir /private/artifacts \
  --output /private/binding-assessment.json
"""
from __future__ import annotations

import argparse
import json
import sys
from .evidence_binding import manifest_template, verify_local_bundle
from .two_node_pilot import read_packet_file, write_private_json


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="operation", required=True)
    temp = sub.add_parser("manifest", help="Create no-clobber private evidence file manifest")
    temp.add_argument("--output", required=True)
    check = sub.add_parser("inspect", help="Check private files against completed field witness")
    check.add_argument("--witness", required=True)
    check.add_argument("--manifest", required=True)
    check.add_argument("--evidence-dir", required=True)
    check.add_argument("--output", required=True)
    args = p.parse_args(argv)
    try:
        if args.operation == "manifest":
            write_private_json(args.output, manifest_template())
            print(json.dumps({"status": "PRIVATE_MANIFEST_CREATED",
                              "hardware_qualified": False}))
            return 0
        witness = read_packet_file(args.witness)
        manifest = read_packet_file(args.manifest)
        result = verify_local_bundle(witness, manifest, args.evidence_dir)
        write_private_json(args.output, result)
        print(json.dumps({
            "status": result["status"], "reasons": result["reasons"],
            "evidence_checks": result["checks"],
            "hardware_qualified": False,
        }, sort_keys=True))
        return 0 if result["status"] == "LOCAL_EVIDENCE_MATCH" else 2
    except (OSError, TypeError, ValueError, UnicodeError, OverflowError):
        print(json.dumps({"status": "HOLD", "reason": "PRIVATE_EVIDENCE_IO_OR_VALIDATION_FAILURE",
                          "hardware_qualified": False}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
