from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v24915_v24914_projection_cap_failure as diagnosis  # noqa: E402


class V24915V24914ProjectionCapFailureDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = diagnosis.build(now=1)

    def test_exact220_failure_partition_is_recovered(self) -> None:
        self.assertEqual(self.value["observed"]["selected"], 220)
        self.assertEqual(self.value["observed"]["worker_failure_fallbacks"], 174)
        self.assertEqual(self.value["observed"]["model_generated_tables"], 46)

    def test_failure_stops_before_projection_and_synthesis(self) -> None:
        self.assertEqual(
            self.value["observed"]["last_safe_progress_stage_counts"],
            {"retrieval_terminal": 174, "terminal": 46},
        )
        self.assertEqual(
            self.value["observed"]["fallback_model_request_count_distribution"],
            {1: 174},
        )
        self.assertEqual(
            self.value["observed"]["fallback_projected_character_count_distribution"],
            {0: 174},
        )

    def test_production_shaped_failure_is_reproduced(self) -> None:
        report = self.value["synthetic_reproduction"]
        self.assertTrue(report["failure_reproduced"])
        self.assertTrue(report["first_error_matches_structural_selection_cap"])
        self.assertGreater(report["projection_cap_failures"], 0)

    def test_root_cause_is_unaccounted_join_separator(self) -> None:
        root = self.value["root_cause"]
        self.assertEqual(
            root["mechanism"],
            "selector_accounts_block_content_but_join_inserts_unaccounted_newlines",
        )
        self.assertTrue(root["v24911_nonengagement_masked_bug"])
        self.assertFalse(root["transport_or_gpt56_endpoint_failure"])

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
