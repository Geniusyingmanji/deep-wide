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

from scripts import diagnose_v24577_v24572_prededup_reachability as target  # noqa: E402


class V24577PrededupReachabilityDiagnosisTests(unittest.TestCase):
    def test_counterexample_proves_current_pipeline_erases_replacement_surface(self) -> None:
        value = target.build_diagnosis(now=0)
        counts = value["synthetic_counterexample"]
        self.assertEqual(counts["exact_url_distinct_visible_lead_count"], 3)
        self.assertEqual(counts["post_v24371_unique_source_lead_count"], 2)
        self.assertEqual(counts["pre_dedup_duplicate_source_lead_count"], 1)
        self.assertEqual(
            counts["pre_dedup_validator_aligned_title_replacement_count"], 1
        )
        self.assertEqual(counts["current_pipeline_duplicate_source_lead_count"], 0)
        self.assertEqual(
            counts["current_pipeline_validator_aligned_title_replacement_count"],
            0,
        )

    def test_conclusion_revokes_external_protocol_design_and_launch(self) -> None:
        value = target.validate_diagnosis(target.build_diagnosis(now=0))
        self.assertFalse(
            value["conclusions"]["v24572_current_real_pipeline_mechanism_reachable"]
        )
        self.assertTrue(
            value["conclusions"][
                "pre_dedup_candidate_preservation_required_before_new_external_population"
            ]
        )
        self.assertFalse(value["authorization"]["fresh_external_protocol_design"])
        self.assertFalse(
            value["authorization"]["fresh_external_activation_or_launch"]
        )
        self.assertFalse(value["authorization"]["paired_dev64_or_exact220"])

    def test_diagnosis_is_content_free_label_blind_and_has_no_external_effect(self) -> None:
        value = target.build_diagnosis(now=0)
        policy = value["source_policy"]
        self.assertTrue(policy["visible_title_url_and_registrable_source_only"])
        self.assertFalse(policy["page_content_candidate_value_entropy_or_evaluator_used"])
        self.assertFalse(
            policy[
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
            ]
        )
        self.assertFalse(policy["network_model_search_fetch_process_or_evaluator_called"])
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        accesses, imports = audit.ast_findings(
            Path("scripts/diagnose_v24577_v24572_prededup_reachability.py")
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
