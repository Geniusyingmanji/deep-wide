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

from scripts import diagnose_v25008_v25007_detail_field_link_phase as diagnosis  # noqa: E402


class V25008V25007DetailFieldLinkPhaseDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = diagnosis.build_diagnosis(now=1)

    def test_changed_subset_fetches_succeed_but_records_do_not_convert(self) -> None:
        changed = self.value["selection_changed_subset"]
        second = changed["phase_counts"]["second_wave_union"]
        self.assertEqual(changed["tasks"], 6)
        self.assertEqual(changed["bound_visible_link_gain"], 7)
        self.assertEqual(second["physical_fetches"], 31)
        self.assertEqual(second["usable_pages"], 31)
        self.assertEqual(second["projected_pages"], 31)
        self.assertEqual(second["fetch_failures"], 0)
        self.assertEqual(second["projection_failures"], 0)
        self.assertEqual(second["discovered_records"], 0)
        self.assertEqual(second["retained_records"], 0)
        self.assertEqual(second["exact_parent_prefix_handoffs"], 31)

    def test_arm_effect_is_matched_and_prediction_does_not_change(self) -> None:
        changed = self.value["selection_changed_subset"]
        self.assertEqual(len(set(changed["arm_usable_pages"].values())), 1)
        self.assertEqual(set(changed["target_bound_projected_pages"].values()), {0})
        self.assertEqual(set(changed["target_bound_records"].values()), {0})
        self.assertEqual(changed["prediction_changed_tasks"], 0)

    def test_causal_elimination_preserves_identifiability_boundary(self) -> None:
        conclusion = self.value["causal_elimination"]
        self.assertFalse(
            conclusion["selected_union_fetch_failure_explains_zero_increment"]
        )
        self.assertFalse(
            conclusion["projector_process_exception_explains_zero_increment"]
        )
        self.assertFalse(conclusion["compact_record_capacity_explains_zero_increment"])
        self.assertTrue(conclusion["record_conversion_before_compact_admission_failed"])
        self.assertFalse(conclusion["unique_attribution_available"])
        self.assertGreaterEqual(
            len(conclusion["remaining_not_identifiable_from_frozen_counts"]), 4
        )

    def test_report_is_deidentified_and_effect_free(self) -> None:
        serialized = json.dumps(self.value, ensure_ascii=False, sort_keys=True)
        self.assertIsNone(re.search(r"task_[0-9a-f]{24}", serialized))
        self.assertNotIn("https://", serialized)
        source = self.value["source_policy"]
        self.assertEqual(
            source["decoded_top_level_members"], sorted(diagnosis.SAFE_MEMBERS)
        )
        self.assertFalse(
            source[
                "opaque_id_question_query_url_anchor_page_record_value_prediction_answer_gold_evaluator_row_or_credential_decoded"
            ]
        )
        self.assertFalse(source["network_model_search_fetch_process_or_evaluator_effect"])
        self.assertFalse(source["entropy_or_information_gain_assigns_signed_credit"])

    def test_scanner_decodes_only_safe_members(self) -> None:
        path = diagnosis.ROOT / diagnosis.contract.TASK_RESULTS
        first = next(line for line in path.read_text(encoding="utf-8").splitlines() if line)
        safe = diagnosis.safe_top_level_members(first)
        self.assertEqual(set(safe), diagnosis.SAFE_MEMBERS)
        self.assertNotIn("predictions", safe)
        self.assertNotIn("opaque_id", safe)

    def test_resealed_overclaim_is_rejected(self) -> None:
        altered = copy.deepcopy(self.value)
        altered["causal_elimination"]["unique_attribution_available"] = True
        altered.pop("diagnosis_payload_sha256")
        altered["diagnosis_payload_sha256"] = diagnosis.contract.payload_sha256(altered)
        with self.assertRaises(RuntimeError):
            diagnosis.validate_diagnosis(altered)


if __name__ == "__main__":
    unittest.main()
