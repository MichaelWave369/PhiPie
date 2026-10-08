"""PhiPie two-node field witness CLI. Writes locally only; never publishes.

python -m trailcore.field_cli template --output /private/field-trial.json
python -m trailcore.field_cli host --output /private/local-host.json
python -m trailcore.field_cli assess --input /private/field-trial.json --output /private/field-assessment.json
"""
from __future__ import annotations

import argparse
import json
import sys

from .field_host import capture_host
from .field_witness import assess_witness, template
from .two_node_pilot import read_packet_file, write_private_json


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    for name in ("template", "host"):
        p = sub.add_parser(name, help="Create a new owner-only local file")
        p.add_argument("--output", required=True)
    a = sub.add_parser("assess", help="Review manually populated two-Pi evidence")
    a.add_argument("--input", required=True)
    a.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.operation == "template":
            write_private_json(args.output, template())
            print(json.dumps({"status": "TEMPLATE_CREATED", "physical_qualification": False}))
            return 0
        if args.operation == "host":
            write_private_json(args.output, capture_host())
            print(json.dumps({"status": "HOST_SNAPSHOT_WRITTEN", "hardware_attested": False}))
            return 0
        report = assess_witness(read_packet_file(args.input))
        write_private_json(args.output, report)
        print(json.dumps({"status": report["status"], "reasons": report["reasons"],
                          "hardware_physically_qualified": False}))
        return 0 if report["status"] == "OPERATOR_REVIEW_CANDIDATE" else 2
    except (OSError, TypeError, ValueError, OverflowError, UnicodeError):
        print(json.dumps({"status": "HOLD", "reason": "PRIVATE_EVIDENCE_IO_OR_VALIDATION_FAILURE",
                          "hardware_physically_qualified": False}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
