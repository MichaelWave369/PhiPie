from __future__ import annotations

from typing import Any

from .io import ActuatorAdapter, NullActuatorAdapter, SensorAdapter
from .model import ActionDecision, HostState, PhysicalHostController


class PhysicalHostRuntime:
    """Binds deterministic control to explicit sensor/actuator adapters.

    The runtime never forwards REVIEW or DENY actions to the actuator adapter.
    Adapter exceptions become local PROTECT events with receipts.
    """

    def __init__(
        self,
        *,
        controller: PhysicalHostController,
        sensors: SensorAdapter,
        actuators: ActuatorAdapter | None = None,
    ) -> None:
        self.controller = controller
        self.sensors = sensors
        self.actuators = actuators or NullActuatorAdapter()

    def boot(self) -> dict[str, Any]:
        return self.controller.boot(self.sensors.read())

    def poll(self) -> dict[str, Any]:
        return self.controller.ingest(self.sensors.read())

    def submit_action(
        self,
        *,
        capability: str,
        requested_value: Any,
        requested_by: str,
        authority_granted: bool = False,
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        request_receipt = self.controller.request_action(
            capability=capability,
            requested_value=requested_value,
            requested_by=requested_by,
            authority_granted=authority_granted,
        )

        action = request_receipt["action"]
        decision = request_receipt["decision"]
        executed_value = action.get("executed_value")

        if decision not in {
            ActionDecision.ALLOW.value,
            ActionDecision.CLAMP.value,
        } or executed_value is None:
            return request_receipt, None

        before = self.controller.state
        try:
            adapter_result = self.actuators.execute(capability, executed_value)
        except Exception as exc:
            if self.controller.state != HostState.FAULT_LATCH:
                self.controller.state = HostState.PROTECT
            execution_receipt = self.controller.receipts.append(
                source_plane="action",
                event_kind="action_execution",
                state_before=before,
                state_after=self.controller.state,
                inputs=self.controller.last_snapshot.to_dict()
                if self.controller.last_snapshot
                else {},
                decision="fault",
                action={
                    "capability": capability,
                    "executed_value": executed_value,
                    "adapter_result": None,
                },
                reason=f"actuator adapter failed: {exc}",
            )
            return request_receipt, execution_receipt

        execution_receipt = self.controller.receipts.append(
            source_plane="action",
            event_kind="action_execution",
            state_before=before,
            state_after=self.controller.state,
            inputs=self.controller.last_snapshot.to_dict()
            if self.controller.last_snapshot
            else {},
            decision="executed",
            action={
                "capability": capability,
                "executed_value": executed_value,
                "adapter_result": adapter_result,
            },
            reason="bounded action delivered to configured actuator adapter",
        )
        return request_receipt, execution_receipt
