from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24630_exact220_contract import payload_sha256  # noqa: E402
from scripts import simulate_v24632_capacity_schedules as target  # noqa: E402


class V24632CapacityScheduleSimulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_report(ROOT, now=1)

    def test_calibration_denominators_and_quantiles(self) -> None:
        calibration = self.value["calibration"]
        self.assertEqual(calibration["model_generated_tasks"], 186)
        self.assertEqual(calibration["provider_requests"], 375)
        summaries = calibration["vector_summaries"]
        self.assertEqual(summaries["plan_service_seconds"]["count"], 186)
        self.assertEqual(summaries["postplan_service_seconds"]["count"], 189)
        self.assertAlmostEqual(
            calibration["scenarios"]["p50"]["plan_service_seconds"],
            8.262696,
            places=6,
        )
        self.assertAlmostEqual(
            calibration["scenarios"]["p95"]["postplan_service_seconds"],
            33.744256,
            places=6,
        )
        self.assertTrue(
            calibration["limitations"][
                "aggregate_slot_wait_not_identified_per_effect"
            ]
        )

    def test_workload_matches_frozen_logical_effect_count(self) -> None:
        workload = self.value["workload"]
        self.assertEqual(workload["anonymous_tasks"], 220)
        self.assertEqual(workload["plan_effects"], 220)
        self.assertEqual(workload["initial_synthesis_effects"], 220)
        self.assertEqual(workload["recovery_effects"], 20)
        self.assertEqual(workload["repair_effects"], 2)
        self.assertEqual(workload["total_model_effects"], 462)
        self.assertFalse(
            workload[
                "additional_model_search_or_fetch_work_vs_v24630_logical_accounting"
            ]
        )

    def test_current_schedule_is_not_tail_robust(self) -> None:
        results = self.value["current_schedule_sensitivity"]["scenario_results"]
        self.assertEqual(results["p25"]["effect_window_deadline_misses"], 0)
        self.assertEqual(results["p50"]["effect_window_deadline_misses"], 10)
        self.assertEqual(results["p75"]["effect_window_deadline_misses"], 126)
        self.assertEqual(results["p95"]["effect_window_deadline_misses"], 213)
        self.assertFalse(
            self.value["conclusions"][
                "current_32_8_150_schedule_is_tail_robust_in_simulation"
            ]
        )

    def test_grid_and_selected_schedule_are_deterministic(self) -> None:
        simulation = self.value["simulation"]
        self.assertEqual(simulation["configuration_count"], 72)
        self.assertEqual(simulation["passing_configuration_count"], 7)
        selected = simulation["selected_schedule"]
        self.assertEqual(selected["active_child_cap"], 20)
        self.assertEqual(selected["task_deadline_seconds"], 240)
        self.assertEqual(selected["model_slot_policy"], "fifo")
        tail = selected["scenario_results"]["p95"]
        self.assertEqual(tail["effect_window_deadline_misses"], 0)
        self.assertEqual(tail["task_deadline_misses"], 0)
        self.assertAlmostEqual(
            tail["projected_forward_wall_seconds"], 1621.497780, places=6
        )

    def test_stage_priority_is_not_selected_and_provider_gate_remains(self) -> None:
        conclusions = self.value["conclusions"]
        self.assertTrue(
            conclusions["bounded_active_child_admission_required_by_selected_schedule"]
        )
        self.assertTrue(
            conclusions["longer_task_deadline_required_by_selected_schedule"]
        )
        self.assertFalse(
            conclusions["stage_aware_slot_policy_required_by_selected_schedule"]
        )
        self.assertFalse(conclusions["strict_synthesis_priority_selected"])
        self.assertFalse(conclusions["simulation_proves_real_provider_zero_fallback"])
        self.assertTrue(conclusions["neutral_provider_stress_test_required"])

    def test_content_free_no_benchmark_authority_and_tamper_rejection(self) -> None:
        encoded = json.dumps(self.value, ensure_ascii=False)
        self.assertIsNone(target.SECRET.search(encoded))
        self.assertIsNone(target.OPAQUE.search(encoded))
        self.assertFalse(self.value["authorization"]["neutral_provider_stress_launch"])
        self.assertFalse(self.value["authorization"]["new_exact220"])
        self.assertFalse(self.value["authorization"]["leaderboard_submission"])
        altered = copy.deepcopy(self.value)
        altered["authorization"]["new_exact220"] = True
        altered.pop("simulation_payload_sha256")
        altered["simulation_payload_sha256"] = payload_sha256(altered)
        with self.assertRaisesRegex(RuntimeError, "simulation drifted"):
            target.validate_report(ROOT, altered)


if __name__ == "__main__":
    unittest.main()
