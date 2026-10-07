from __future__ import annotations

import unittest
from datetime import datetime, timezone

from runtime.physical_host import (
    ActionDecision,
    HostState,
    PhysicalHostController,
    SensorSnapshot,
    SyntheticSensorAdapter,
    default_manifest,
    validate_manifest,
)


FIXED_TIME = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)


def fixed_clock() -> datetime:
    return FIXED_TIME


class PhysicalHostSimulatorTests(unittest.TestCase):
    def controller(self) -> PhysicalHostController:
        return PhysicalHostController(clock=fixed_clock)

    def test_default_manifest_preserves_authority_boundary(self) -> None:
        manifest = default_manifest()
        self.assertEqual([], validate_manifest(manifest))
        self.assertTrue(manifest["network_loss_safe"])
        self.assertFalse(manifest["cloud_required_for_safety"])
        self.assertFalse(
            manifest["authority"]["phibot_direct_physical_authority"]
        )

    def test_healthy_boot_requires_explicit_arm(self) -> None:
        ctl = self.controller()
        ctl.boot(SyntheticSensorAdapter.snapshot("healthy"))
        self.assertEqual(HostState.SAFE_IDLE, ctl.state)
        ctl.arm()
        self.assertEqual(HostState.READY, ctl.state)

    def test_network_and_model_loss_do_not_disable_local_safety(self) -> None:
        ctl = self.controller()
        ctl.boot(SyntheticSensorAdapter.snapshot("healthy"))
        ctl.arm()
        receipt = ctl.ingest(SyntheticSensorAdapter.snapshot("network_loss"))
        self.assertEqual(HostState.READY, ctl.state)
        self.assertEqual("observe", receipt["decision"])

        receipt = ctl.ingest(
            SensorSnapshot(network_ok=False, model_ok=False, board_temp_c=90.0)
        )
        self.assertEqual(HostState.PROTECT, ctl.state)
        self.assertEqual("protect", receipt["decision"])

    def test_thermal_derate_then_recovery_requires_rearm(self) -> None:
        ctl = self.controller()
        ctl.boot(SyntheticSensorAdapter.snapshot("healthy"))
        ctl.arm()
        ctl.ingest(SyntheticSensorAdapter.snapshot("thermal_derate"))
        self.assertEqual(HostState.DERATE, ctl.state)
        ctl.ingest(SyntheticSensorAdapter.snapshot("healthy"))
        self.assertEqual(HostState.RECOVERY, ctl.state)
        ctl.arm()
        self.assertEqual(HostState.READY, ctl.state)

    def test_leak_fault_latches_until_safe_snapshot_and_operator_reset(self) -> None:
        ctl = self.controller()
        ctl.boot(SyntheticSensorAdapter.snapshot("healthy"))
        ctl.arm()
        ctl.ingest(SyntheticSensorAdapter.snapshot("leak"))
        self.assertEqual(HostState.FAULT_LATCH, ctl.state)

        ctl.ingest(SyntheticSensorAdapter.snapshot("healthy"))
        self.assertEqual(HostState.FAULT_LATCH, ctl.state)

        denied = ctl.reset_fault(operator_confirmed=False)
        self.assertEqual("deny", denied["decision"])
        self.assertEqual(HostState.FAULT_LATCH, ctl.state)

        allowed = ctl.reset_fault(operator_confirmed=True)
        self.assertEqual("allow", allowed["decision"])
        self.assertEqual(HostState.RECOVERY, ctl.state)

    def test_phibot_has_no_direct_physical_authority(self) -> None:
        ctl = self.controller()
        ctl.boot(SyntheticSensorAdapter.snapshot("healthy"))
        ctl.arm()
        receipt = ctl.request_action(
            capability="load.enable",
            requested_value=True,
            requested_by="phibot",
            authority_granted=False,
        )
        self.assertEqual(ActionDecision.REVIEW.value, receipt["decision"])
        self.assertEqual(HostState.READY, ctl.state)
        self.assertIsNone(receipt["action"]["executed_value"])

    def test_explicit_grant_still_passes_plane_a_state_gate(self) -> None:
        ctl = self.controller()
        ctl.boot(SyntheticSensorAdapter.snapshot("thermal_protect"))
        receipt = ctl.request_action(
            capability="load.enable",
            requested_value=True,
            requested_by="phibot",
            authority_granted=True,
        )
        self.assertEqual(ActionDecision.DENY.value, receipt["decision"])
        self.assertEqual(HostState.PROTECT, ctl.state)

    def test_explicit_grant_can_enable_bounded_load_when_ready(self) -> None:
        ctl = self.controller()
        ctl.boot(SyntheticSensorAdapter.snapshot("healthy"))
        ctl.arm()
        receipt = ctl.request_action(
            capability="load.enable",
            requested_value=True,
            requested_by="phibot",
            authority_granted=True,
        )
        self.assertEqual(ActionDecision.ALLOW.value, receipt["decision"])
        self.assertTrue(receipt["action"]["executed_value"])
        self.assertEqual(HostState.ACTIVE, ctl.state)

    def test_fan_request_is_clamped(self) -> None:
        ctl = self.controller()
        ctl.boot(SyntheticSensorAdapter.snapshot("healthy"))
        receipt = ctl.request_action(
            capability="fan.set",
            requested_value=140,
            requested_by="system",
        )
        self.assertEqual(ActionDecision.CLAMP.value, receipt["decision"])
        self.assertEqual(100.0, receipt["action"]["executed_value"])

    def test_receipt_chain_detects_tampering(self) -> None:
        ctl = self.controller()
        ctl.boot(SyntheticSensorAdapter.snapshot("healthy"))
        ctl.arm()
        self.assertTrue(ctl.receipts.verify())
        ctl.receipts.receipts[0]["reason"] = "tampered"
        self.assertFalse(ctl.receipts.verify())


if __name__ == "__main__":
    unittest.main()
