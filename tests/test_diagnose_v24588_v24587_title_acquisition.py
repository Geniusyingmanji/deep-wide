from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v24588_v24587_title_acquisition as target  # noqa: E402


class V24588V24587TitleAcquisitionDiagnosisTests(unittest.TestCase):
    def test_public_counts_separate_repaired_dedup_from_title_boundary(self) -> None:
        value = target.build_diagnosis(now=0)
        engineering = value["engineering_outcome"]
        mechanism = value["mechanism_boundary"]
        self.assertEqual(engineering["success_tasks"], 8)
        self.assertEqual(engineering["failure_as_zero_tasks"], 0)
        self.assertFalse(engineering["inherited_original_task_projection_rebound"])
        self.assertGreater(mechanism["preserved_candidate_count"], 0)
        self.assertGreater(mechanism["source_representative_replacement_count"], 0)
        self.assertEqual(mechanism["validator_aligned_title_replacement_count"], 0)

    def test_all_observed_title_hits_were_excluded_and_none_selected(self) -> None:
        mechanism = target.build_diagnosis(now=0)["mechanism_boundary"]
        self.assertGreater(mechanism["title_alias_surface_hit_lead_count"], 0)
        self.assertEqual(
            mechanism["title_alias_surface_hit_lead_count"],
            mechanism["excluded_title_alias_surface_hit_lead_count"],
        )
        self.assertEqual(mechanism["selected_title_alias_surface_hit_lead_count"], 0)

    def test_conclusion_does_not_overattribute_absence(self) -> None:
        conclusions = target.build_diagnosis(now=0)["conclusions"]
        self.assertTrue(conclusions["v24585_immutable_collector_failure_mode_repaired"])
        self.assertTrue(conclusions["pre_dedup_candidate_preservation_is_runtime_reachable"])
        self.assertFalse(conclusions["absence_proves_title_validator_is_too_strict"])
        self.assertFalse(
            conclusions["absence_proves_search_provider_cannot_return_title_hits"]
        )
        self.assertFalse(
            conclusions[
                "population_specific_surface_mismatch_or_source_exclusion_ruled_out"
            ]
        )

    def test_authorization_is_policy_design_only(self) -> None:
        authorization = target.build_diagnosis(now=0)["authorization"]
        self.assertTrue(authorization["validator_aligned_title_query_policy_design"])
        self.assertFalse(authorization["fresh_external_protocol_design"])
        self.assertFalse(authorization["fresh_external_activation_or_launch"])
        self.assertFalse(authorization["paired_dev64_or_exact220"])
        self.assertFalse(authorization["evaluator_access_authorized"])

    def test_source_policy_is_public_content_free_and_label_blind(self) -> None:
        policy = target.build_diagnosis(now=0)["source_policy"]
        self.assertTrue(policy["sealed_public_aggregate_decision_and_postaudit_only"])
        self.assertFalse(
            policy[
                "task_question_query_url_page_prediction_candidate_value_or_private_directory_opened"
            ]
        )
        self.assertFalse(
            policy[
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
            ]
        )
        self.assertFalse(policy["network_model_search_fetch_process_or_evaluator_called"])
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        accesses, imports = audit.ast_findings(
            Path("scripts/diagnose_v24588_v24587_title_acquisition.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])

    def test_resealed_tamper_fails_closed(self) -> None:
        value = target.build_diagnosis(now=0)
        changed = copy.deepcopy(value)
        changed["authorization"]["fresh_external_protocol_design"] = True
        changed.pop("diagnosis_payload_sha256")
        changed["diagnosis_payload_sha256"] = target.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_diagnosis(changed)

    def test_publisher_is_create_only(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "diagnosis.json"
            target.publish_new(path, {})
            with self.assertRaises(FileExistsError):
                target.publish_new(path, {})


if __name__ == "__main__":
    unittest.main()
