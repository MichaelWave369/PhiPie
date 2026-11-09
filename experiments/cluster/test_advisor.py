"""Contract and conservative-path tests for synthetic PhiCluster advisor."""
import copy
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from advisor import ContractError, ZERO_HASH, advise, utc_time  # noqa: E402

EXAMPLE = Path(__file__).with_name("scenario.json")
AT = datetime(2026, 11, 8, 12, 0, 30, tzinfo=timezone.utc)


def scenario():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


class AdvisorTests(unittest.TestCase):
    def test_healthy_three_node_example(self):
        plan = advise(scenario(), now=AT)
        self.assertEqual("normal", plan["power_mode"])
        self.assertEqual(3, len(plan["decisions"]))
        self.assertEqual({"propose"}, {d["decision"] for d in plan["decisions"]})
        self.assertEqual({"pie-control-01", "pie-service-01", "pie-vault-01"},
                         {d["proposed_node_id"] for d in plan["decisions"]})
        self.assertTrue(plan["simulation_only"])
        self.assertTrue(plan["no_execution"])
        self.assertFalse(plan["qualifies_hardware"])
        self.assertTrue(all(d["action_executed"] is False for d in plan["decisions"]))

    def test_stale_power_telemetry_defers_everything(self):
        payload = scenario()
        plan = advise(payload, now=datetime(2026, 11, 8, 12, 3, 0, tzinfo=timezone.utc))
        self.assertEqual("untrusted", plan["power_mode"])
        self.assertTrue(all(d["decision"] == "defer" for d in plan["decisions"]))

    def test_future_dated_telemetry_defers_everything(self):
        payload = scenario()
        plan = advise(payload, now=datetime(2026, 11, 8, 11, 0, tzinfo=timezone.utc))
        self.assertEqual("untrusted", plan["power_mode"])

    def test_unknown_supply_mode_defers_all(self):
        payload = scenario()
        payload["power"]["supply_mode"] = "unknown"
        plan = advise(payload, now=AT)
        self.assertEqual("untrusted", plan["power_mode"])
        self.assertTrue(all(d["decision"] == "defer" for d in plan["decisions"]))

    def test_critical_battery_refuses_new_placements(self):
        payload = scenario()
        payload["power"]["battery_soc_pct"] = 19
        plan = advise(payload, now=AT)
        self.assertEqual("critical", plan["power_mode"])
        self.assertEqual(0, plan["proposed_incremental_w"])

    def test_conservation_only_considers_essential(self):
        payload = scenario()
        payload["power"]["battery_soc_pct"] = 40
        plan = advise(payload, now=AT)
        self.assertEqual("conservation", plan["power_mode"])
        self.assertEqual("propose", next(d for d in plan["decisions"] if d["job_id"] == "dashboard")["decision"])
        self.assertEqual("defer", next(d for d in plan["decisions"] if d["job_id"] == "indexer")["decision"])

    def test_unknown_battery_health_defers(self):
        payload = scenario()
        payload["power"]["battery_health"] = "unknown"
        plan = advise(payload, now=AT)
        self.assertEqual("untrusted", plan["power_mode"])
        self.assertEqual(0, plan["proposed_incremental_w"])

    def test_no_fake_authority_from_capability(self):
        payload = scenario()
        payload["jobs"][0]["simulated_grant"] = False
        plan = advise(payload, now=AT)
        self.assertEqual("deny", next(d for d in plan["decisions"] if d["job_id"] == "dashboard")["decision"])

    def test_budget_does_not_overcommit(self):
        payload = scenario()
        payload["power"]["safe_incremental_w"] = 9
        plan = advise(payload, now=AT)
        self.assertLessEqual(plan["proposed_incremental_w"], 9)
        self.assertTrue(any(d["decision"] == "defer" for d in plan["decisions"]))

    def test_node_state_refuses_assignment(self):
        payload = scenario()
        payload["nodes"][1]["state"] = "offline"
        plan = advise(payload, now=AT)
        self.assertEqual("defer", next(d for d in plan["decisions"] if d["job_id"] == "indexer")["decision"])

    def test_duplicate_job_id_fails_closed(self):
        payload = scenario()
        payload["jobs"][1]["job_id"] = payload["jobs"][0]["job_id"]
        with self.assertRaises(ContractError):
            advise(payload, now=AT)

    def test_nonfinite_power_fails_closed(self):
        payload = scenario()
        payload["power"]["safe_incremental_w"] = float("nan")
        with self.assertRaises(ContractError):
            advise(payload, now=AT)

    def test_receipts_chain_and_deterministic_output(self):
        one = advise(scenario(), now=AT)
        two = advise(scenario(), now=AT)
        self.assertEqual(one, two)
        self.assertEqual(ZERO_HASH, one["receipts"][0]["previous_hash"])
        for previous, current in zip(one["receipts"], one["receipts"][1:]):
            self.assertEqual(previous["current_hash"], current["previous_hash"])
        self.assertEqual(one["receipt_head"], one["receipts"][-1]["current_hash"])

    def test_bad_telemetry_source_is_rejected(self):
        payload = scenario()
        payload["power"]["source"] = "live"
        with self.assertRaises(ContractError):
            advise(payload, now=AT)

    def test_utc_required(self):
        with self.assertRaises(ContractError):
            utc_time("2026-11-08T12:00:00-08:00")


if __name__ == "__main__":
    unittest.main()
