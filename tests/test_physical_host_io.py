from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from runtime.physical_host import (
    HostState,
    PhysicalHostController,
    SyntheticSensorAdapter,
    default_manifest,
    validate_manifest,
)
from runtime.physical_host.io import (
    RecordingActuatorAdapter,
    ScenarioSensorAdapter,
)
from runtime.physical_host.runtime import PhysicalHostRuntime


FIXED_TIME = datetime(2026, 10, 7, 13, 0, tzinfo=timezone.utc)


def fixed_clock() -> datetime:
    return FIXED_TIME


class PhysicalHostIOTests(unittest.TestCase):
    def runtime(
        self, actuator: RecordingActuatorAdapter | None = None
    ) -> PhysicalHostRuntime:
        controller = PhysicalHostController(clock=fixed_clock)
        return PhysicalHostRuntime(
            controller=controller,
            sensors=ScenarioSensorAdapter("healthy"),
            actuators=actuator or RecordingActuatorAdapter(),
        )

    def test_phibot_review_never_reaches_actuator_adapter(self) -> None:
        adapter = RecordingActuatorAdapter()
        rt = self.runtime(adapter)
        rt.boot()
        rt.controller.arm()

        request, execution = rt.submit_action(
            capability="load.enable",
            requested_value=True,
            requested_by="phibot",
            authority_granted=False,
        )

        self.assertEqual("review", request["decision"])
        self.assertIsNone(execution)
        self.assertEqual([], adapter.calls)

    def test_denied_action_never_reaches_actuator_adapter(self) -> None:
        adapter = RecordingActuatorAdapter()
        ctl = PhysicalHostController(clock=fixed_clock)
        ctl.boot(SyntheticSensorAdapter.snapshot("thermal_protect"))
        rt = PhysicalHostRuntime(
            controller=ctl,
            sensors=ScenarioSensorAdapter("healthy"),
            actuators=adapter,
        )

        request, execution = rt.submit_action(
            capability="load.enable",
            requested_value=True,
            requested_by="operator",
            authority_granted=True,
        )

        self.assertEqual("deny", request["decision"])
        self.assertIsNone(execution)
        self.assertEqual([], adapter.calls)

    def test_allowed_action_crosses_adapter_boundary_once(self) -> None:
        adapter = RecordingActuatorAdapter()
        rt = self.runtime(adapter)
        rt.boot()
        rt.controller.arm()

        request, execution = rt.submit_action(
            capability="load.enable",
            requested_value=True,
            requested_by="operator",
            authority_granted=True,
        )

        self.assertEqual("allow", request["decision"])
        self.assertIsNotNone(execution)
        self.assertEqual("executed", execution["decision"])
        self.assertEqual(
            [{"capability": "load.enable", "value": True}],
            adapter.calls,
        )

    def test_clamped_action_crosses_boundary_with_bounded_value(self) -> None:
        adapter = RecordingActuatorAdapter()
        rt = self.runtime(adapter)
        rt.boot()

        request, execution = rt.submit_action(
            capability="fan.set",
            requested_value=140,
            requested_by="system",
        )

        self.assertEqual("clamp", request["decision"])
        self.assertIsNotNone(execution)
        self.assertEqual(
            [{"capability": "fan.set", "value": 100.0}],
            adapter.calls,
        )

    def test_actuator_failure_forces_protect_and_receipt(self) -> None:
        adapter = RecordingActuatorAdapter(fail_capabilities={"load.enable"})
        rt = self.runtime(adapter)
        rt.boot()
        rt.controller.arm()

        request, execution = rt.submit_action(
            capability="load.enable",
            requested_value=True,
            requested_by="operator",
            authority_granted=True,
        )

        self.assertEqual("allow", request["decision"])
        self.assertIsNotNone(execution)
        self.assertEqual("fault", execution["decision"])
        self.assertEqual(HostState.PROTECT, rt.controller.state)
        self.assertTrue(rt.controller.receipts.verify())

    def test_example_manifest_matches_runtime_contract(self) -> None:
        path = Path("examples/physical_host/lab-node.manifest.json")
        manifest = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(default_manifest(), manifest)
        self.assertEqual([], validate_manifest(manifest))

    def test_schema_documents_and_generated_receipt_share_required_keys(self) -> None:
        manifest_schema = json.loads(
            Path("contracts/physical_host/manifest-v0.1.schema.json").read_text(
                encoding="utf-8"
            )
        )
        receipt_schema = json.loads(
            Path("contracts/physical_host/receipt-v0.1.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("host_id", manifest_schema["required"])

        ctl = PhysicalHostController(clock=fixed_clock)
        receipt = ctl.boot(SyntheticSensorAdapter.snapshot("healthy"))
        missing = set(receipt_schema["required"]).difference(receipt)
        self.assertEqual(set(), missing)


if __name__ == "__main__":
    unittest.main()
