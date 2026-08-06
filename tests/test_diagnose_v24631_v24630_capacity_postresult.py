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
from scripts import diagnose_v24631_v24630_capacity_postresult as target  # noqa: E402


class V24631V24630CapacityPostresultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_report(ROOT, now=1)

    def test_exact_terminal_and_bundle_denominators(self) -> None:
        aggregate = self.value["aggregate"]
        self.assertEqual(
            aggregate["denominators"],
            {
                "terminal_tasks": 220,
                "complete_child_bundles": 218,
                "terminal_worker_failures": 2,
                "model_generated_tables": 186,
                "fallback_tables": 34,
            },
        )
        self.assertEqual(
            aggregate["parent_exit_taxonomy"],
            {"child_nonzero_with_terminal_receipt": 2, "success": 218},
        )
        self.assertEqual(
            aggregate["child_exception_types"],
            {"ValidationError": 2, "none": 218},
        )

    def test_slot_timeout_and_fallback_cooccur_exactly(self) -> None:
        table = self.value["aggregate"]["slot_timeout_contingency"]
        self.assertEqual(
            table["model_generated"],
            {"without_slot_timeout": 186, "with_slot_timeout": 0},
        )
        self.assertEqual(
            table["fallback"],
            {"without_slot_timeout": 0, "with_slot_timeout": 34},
        )
        conclusions = self.value["conclusions"]
        self.assertTrue(
            conclusions[
                "task_level_slot_timeout_fallback_association_is_perfect_in_this_run"
            ]
        )
        self.assertFalse(
            conclusions["randomized_causal_effect_of_scheduling_established"]
        )

    def test_complete_model_effect_conservation_and_recovery(self) -> None:
        accounting = self.value["aggregate"]["complete_bundle_model_accounting"]
        self.assertEqual(accounting["tasks"], 218)
        self.assertTrue(accounting["conservation_verified"])
        self.assertEqual(accounting["model_slot_acquisitions"], 426)
        self.assertEqual(accounting["model_slot_timeouts"], 32)
        self.assertEqual(
            accounting["totals"],
            {
                "logical_admissions": 458,
                "provider_requests": 426,
                "provider_attempts": 443,
                "pre_provider_rejections": 32,
                "initial_synthesis_errors": 33,
                "recovery_attempted": 20,
                "recovery_succeeded": 2,
                "recovery_failed": 18,
                "repair_blocked_after_recovery": 0,
            },
        )
        stages = accounting["stage_totals"]
        self.assertEqual(
            stages["pre_provider_rejections"],
            {"plan": 0, "synthesis_initial": 13, "synthesis_recovery": 18, "repair": 1},
        )

    def test_terminal_slot_wait_and_evidence_volume_are_bound(self) -> None:
        slot = self.value["aggregate"]["terminal_model_slot_accounting"]
        self.assertEqual(slot["acquisitions"], 427)
        self.assertEqual(slot["slot_timeouts"], 35)
        self.assertEqual(slot["provider_deadline_failures"], 18)
        self.assertEqual(slot["tasks_with_slot_timeout"], 34)
        self.assertAlmostEqual(slot["total_wait_seconds"], 10224.904228, places=6)
        evidence = self.value["aggregate"]["evidence_and_latency"]
        self.assertEqual(evidence["model_generated_projected_chars"]["count"], 186)
        self.assertEqual(
            evidence["best_effort_fallback_projected_chars"]["count"], 32
        )
        self.assertAlmostEqual(
            evidence[
                "best_effort_to_model_generated_mean_projected_chars_ratio"
            ],
            0.953423,
            places=6,
        )

    def test_backfill_is_zero_effect_and_diagnosis_has_no_benchmark_authority(self) -> None:
        self.assertEqual(
            self.value["backfill"],
            {
                "backfilled_unique_urls": 40,
                "query_local_shadowed_backfilled_urls": 40,
                "surviving_downstream_leads": 0,
                "downstream_candidate_set_changed": False,
            },
        )
        self.assertFalse(self.value["authorization"]["additional_dev64"])
        self.assertFalse(self.value["authorization"]["new_exact220"])
        self.assertFalse(self.value["authorization"]["leaderboard_submission"])
        self.assertFalse(self.value["conclusions"]["project_best_or_sota_reached"])

    def test_content_free_and_resealed_tamper_is_rejected(self) -> None:
        encoded = json.dumps(self.value, ensure_ascii=False)
        self.assertIsNone(target.SECRET.search(encoded))
        self.assertIsNone(target.OPAQUE.search(encoded))
        self.assertFalse(self.value["boundary"]["visible_task_files_read"])
        self.assertFalse(self.value["boundary"]["runtime_prediction_rows_read"])
        altered = copy.deepcopy(self.value)
        altered["authorization"]["new_exact220"] = True
        altered.pop("diagnosis_payload_sha256")
        altered["diagnosis_payload_sha256"] = payload_sha256(altered)
        with self.assertRaisesRegex(RuntimeError, "diagnosis drifted"):
            target.validate_report(ROOT, altered)


if __name__ == "__main__":
    unittest.main()
