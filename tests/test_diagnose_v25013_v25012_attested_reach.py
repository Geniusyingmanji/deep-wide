from __future__ import annotations

import copy
import json
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25013_v25012_attested_reach as diagnosis  # noqa: E402


class V25013V25012AttestedReachDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = diagnosis.build_diagnosis(now=1)

    def test_attested_reach_funnel_is_exact(self) -> None:
        selection = self.value["selection_funnel"]
        self.assertEqual(selection["attested_child_detail_link_count"], 15)
        self.assertEqual(selection["available_attested_child_detail_link_count"], 3)
        self.assertEqual(selection["strategy_eligible_tasks"], 2)
        self.assertEqual(selection["selection_changed_tasks"], 2)
        self.assertEqual(selection["attested_child_detail_link_gain"], 2)

    def test_changed_subset_converts_two_of_two_records_and_predictions(self) -> None:
        changed = self.value["changed_subset"]
        stage = changed["second_wave_detail_stage"]
        self.assertEqual(changed["tasks"], 2)
        self.assertEqual(stage["discovered_record_page_count"], 2)
        self.assertEqual(stage["retained_record_page_count"], 2)
        self.assertEqual(
            stage["stage_signature_counts"],
            {"c1p0a1s0f0d0r0": 8, "c1p1a1s1f1d1r1": 2},
        )
        outcomes = self.value["parent_outcome_counts"]
        self.assertEqual(outcomes["tasks_with_positive_record_gain"], 2)
        self.assertEqual(outcomes["selection_and_prediction_changed_tasks"], 2)

    def test_diagnosis_moves_from_conversion_to_coverage(self) -> None:
        causal = self.value["causal_diagnosis"]
        self.assertTrue(causal["changed_subset_record_and_joint_prediction_conversion_complete"])
        self.assertFalse(causal["projector_or_compact_admission_is_current_primary_bottleneck"])
        self.assertTrue(
            causal["single_identity_direct_search_and_prior_fetch_redundancy_is_primary_observed_ceiling"]
        )
        self.assertEqual(
            causal["attested_children_removed_by_combined_prior_self_search_prefix_exclusion"],
            12,
        )
        self.assertEqual(causal["available_attested_child_blocked_by_zero_link_slots"], 1)
        self.assertFalse(
            causal["excluded_attested_children_uniquely_partitionable_by_exclusion_reason"]
        )

    def test_unmatched_prediction_change_gets_no_treatment_credit(self) -> None:
        outcomes = self.value["parent_outcome_counts"]
        self.assertEqual(outcomes["prediction_changed_tasks"], 3)
        self.assertEqual(outcomes["prediction_changed_without_selection_change_tasks"], 1)
        self.assertFalse(
            self.value["causal_diagnosis"][
                "prediction_change_without_selection_change_is_treatment_credit"
            ]
        )

    def test_report_is_deidentified_and_effect_free(self) -> None:
        serialized = json.dumps(self.value, ensure_ascii=False, sort_keys=True)
        self.assertIsNone(re.search(r"task_[0-9a-f]{24}", serialized))
        self.assertNotIn("https://", serialized)
        source = self.value["source_policy"]
        self.assertFalse(
            source[
                "opaque_id_question_query_url_anchor_page_record_value_prediction_text_answer_gold_evaluator_row_or_credential_decoded"
            ]
        )
        self.assertFalse(source["network_model_search_fetch_process_or_evaluator_effect"])
        self.assertFalse(source["entropy_or_information_gain_assigns_signed_credit"])

    def test_scanner_decodes_only_explicit_content_free_surfaces(self) -> None:
        line = next(
            value
            for value in (diagnosis.ROOT / diagnosis.contract.TASK_RESULTS)
            .read_text(encoding="utf-8")
            .splitlines()
            if value
        )
        row = diagnosis.safe_row(line)
        self.assertEqual(
            set(row), {"attested", "observers", "content", "prediction_changed"}
        )
        self.assertNotIn("predictions", row)
        self.assertNotIn("opaque_id", row)

    def test_resealed_overclaim_is_rejected(self) -> None:
        changed = copy.deepcopy(self.value)
        changed["causal_diagnosis"][
            "projector_or_compact_admission_is_current_primary_bottleneck"
        ] = True
        changed.pop("diagnosis_payload_sha256")
        changed["diagnosis_payload_sha256"] = diagnosis.contract.payload_sha256(changed)
        with self.assertRaises(RuntimeError):
            diagnosis.validate_diagnosis(changed)


if __name__ == "__main__":
    unittest.main()
