from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v24919_v24918_total_projection_failure as diagnosis  # noqa: E402


class V24919V24918TotalProjectionFailureDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = diagnosis.validate(diagnosis.build(now=1))

    def test_frozen_failure_partition_is_exact(self) -> None:
        aggregate = self.value["aggregate"]
        self.assertEqual(aggregate["selected"], 220)
        self.assertEqual(
            aggregate["completion_kind_counts"],
            {
                "normalized_primary": 4,
                "primary": 144,
                "worker_failure_fallback": 72,
            },
        )
        self.assertEqual(
            aggregate["last_safe_progress_stage_counts"],
            {"retrieval_terminal": 72, "terminal": 148},
        )

    def test_fallback_receipt_is_postfailure_backfill(self) -> None:
        aggregate = self.value["aggregate"]
        self.assertEqual(
            aggregate["fallback_projection_input_page_distribution"], {"0": 72}
        )
        self.assertGreater(
            aggregate["fallback_transport_totals"]["hard_fetch_helper_calls"], 0
        )
        self.assertTrue(
            self.value["mechanical_conclusion"]
            ["empty_projection_receipt_is_postfailure_terminal_backfill_not_zero_retrieval"]
        )

    def test_production_total_cap_failure_is_reproduced(self) -> None:
        synthetic = self.value["synthetic_reproduction"]
        self.assertTrue(synthetic["total_render_overflow_reproduced"])
        self.assertTrue(synthetic["first_error_matches_exact_total_cap"])
        self.assertTrue(synthetic["runtime_binding_exact_total_cap_reproduced"])
        self.assertTrue(synthetic["short_page_control_succeeds"])
        self.assertTrue(synthetic["duplicate_url_control_deduplicates"])

    def test_report_does_not_overclaim_unique_attribution(self) -> None:
        conclusion = self.value["mechanical_conclusion"]
        self.assertFalse(
            conclusion["all_72_failures_uniquely_attributed_from_frozen_artifacts"]
        )
        self.assertIn("coarse_exception", conclusion["reason_unique_attribution_is_unavailable"])

    def test_diagnosis_is_label_blind_and_no_effect(self) -> None:
        self.assertTrue(self.value["diagnosis_valid"])
        self.assertEqual(self.value["findings"], [])
        policy = self.value["source_policy"]
        self.assertFalse(
            policy[
                "runtime_mapping_gold_category_question_type_split_evaluator_score_reward_read"
            ]
        )
        self.assertFalse(
            policy["network_model_search_fetch_or_evaluator_called_by_diagnosis"]
        )
        self.assertFalse(
            policy["entropy_or_information_gain_assigns_signed_credit"]
        )


if __name__ == "__main__":
    unittest.main()
