from __future__ import annotations

import argparse
import json

from .model import PhysicalHostController, SyntheticSensorAdapter


def emit(receipt: dict) -> None:
    print(json.dumps(receipt, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the non-qualifying Phi Physical Host simulator."
    )
    parser.add_argument(
        "--scenario",
        choices=sorted(SyntheticSensorAdapter.SCENARIOS),
        default="healthy",
        help="synthetic sensor scenario to inject after boot",
    )
    args = parser.parse_args()

    controller = PhysicalHostController()
    emit(controller.boot(SyntheticSensorAdapter.snapshot("healthy")))
    emit(controller.arm())

    # Demonstrate that a PhiBot request is not direct physical authority.
    emit(
        controller.request_action(
            capability="load.enable",
            requested_value=True,
            requested_by="phibot",
            authority_granted=False,
        )
    )

    # Demonstrate the same bounded request after an explicit external grant.
    emit(
        controller.request_action(
            capability="load.enable",
            requested_value=True,
            requested_by="phibot",
            authority_granted=True,
        )
    )

    emit(controller.ingest(SyntheticSensorAdapter.snapshot(args.scenario)))

    summary = {
        "scenario": args.scenario,
        "final_state": controller.state.value,
        "receipt_count": len(controller.receipts.receipts),
        "receipt_chain_valid": controller.receipts.verify(),
        "network_or_model_required_for_safety": False,
        "qualification_claim": False,
    }
    print(json.dumps({"summary": summary}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
