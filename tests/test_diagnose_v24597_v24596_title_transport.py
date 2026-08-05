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

from scripts import diagnose_v24597_v24596_title_transport as target  # noqa: E402


class V24597V24596TitleTransportDiagnosisTests(unittest.TestCase):
    def test_query_candidate_and_selection_paths_were_reached(self) -> None:
        value = target.build_diagnosis(now=0)
        funnel = value["acquisition_funnel"]
        self.assertEqual(funnel["title_query_activity_tasks"], 7)
        self.assertEqual(funnel["title_query_activity_tasks"], funnel["target_plan_tasks"])
        self.assertEqual(funnel["logical_query_count"], 2 * funnel["query_vector_calls"])
        self.assertGreater(funnel["preserved_candidate_count"], 0)
        self.assertGreater(funnel["source_representative_replacement_count"], 0)

    def test_url_surface_exists_but_strict_title_surface_is_zero(self) -> None:
        funnel = target.build_diagnosis(now=0)["acquisition_funnel"]
        self.assertGreater(funnel["visible_lead_count"], 0)
        self.assertGreater(funnel["url_alias_surface_hit_lead_count"], 0)
        self.assertGreater(funnel["selected_url_alias_surface_hit_lead_count"], 0)
        self.assertEqual(funnel["title_alias_surface_hit_lead_count"], 0)
        self.assertEqual(funnel["validator_aligned_title_replacement_count"], 0)

    def test_zero_title_hit_is_not_overattributed(self) -> None:
        conclusions = target.build_diagnosis(now=0)["conclusions"]
        for name in (
            "zero_strict_title_hits_proves_search_result_titles_are_empty",
            "zero_strict_title_hits_proves_row_tokens_are_absent_from_titles",
            "zero_strict_title_hits_proves_alias_match_start_limit_is_too_strict",
            "zero_strict_title_hits_proves_type_compatibility_is_too_strict",
            "cross_population_comparison_proves_v24589_query_policy_hurt_recall",
        ):
            self.assertFalse(conclusions[name])
        self.assertFalse(
            conclusions[
                "public_aggregate_distinguishes_empty_absent_late_and_type_incompatible_title_failure"
            ]
        )

    def test_next_step_is_content_free_title_funnel_only(self) -> None:
        value = target.build_diagnosis(now=0)
        required = value["required_next_observability"]
        self.assertTrue(required["nonempty_title_lead_count"])
        self.assertTrue(required["surface_rejected_only_by_maximum_start_count"])
        self.assertTrue(required["surface_rejected_only_by_type_compatibility_count"])
        self.assertFalse(required["raw_title_query_url_or_page_text_emitted"])
        authorization = value["authorization"]
        self.assertTrue(authorization["content_free_title_transport_observability_design"])
        self.assertFalse(authorization["query_policy_or_title_validator_change"])
        self.assertFalse(authorization["fresh_external_protocol_design"])
        self.assertFalse(authorization["paired_dev64_or_exact220"])

    def test_source_policy_is_public_content_free_and_label_blind(self) -> None:
        policy = target.build_diagnosis(now=0)["source_policy"]
        self.assertTrue(policy["sealed_public_aggregate_decision_and_postaudit_only"])
        self.assertFalse(
            policy[
                "task_question_query_url_title_page_prediction_candidate_value_or_private_directory_opened"
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
            Path("scripts/diagnose_v24597_v24596_title_transport.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])

    def test_resealed_tamper_fails_closed(self) -> None:
        value = target.build_diagnosis(now=0)
        changed = copy.deepcopy(value)
        changed["authorization"]["query_policy_or_title_validator_change"] = True
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
