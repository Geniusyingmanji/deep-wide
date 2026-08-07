from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v24769_zero_effect_reachability as target  # noqa: E402


class V24769ZeroEffectReachabilityDiagnosisTests(unittest.TestCase):
    def test_replay_separates_all_cell_upper_bound_from_unknown_surface(self) -> None:
        value = target.build_diagnosis(now=0)
        replay = value["strict_v24365_replay"]
        all_cells = replay["all_value_cells_counterfactual"]
        unknown = replay["actual_unknown_cells"]
        self.assertEqual(all_cells["semantic_projection_count"], 14)
        self.assertEqual(all_cells["candidate_target_value_group_count"], 43)
        self.assertEqual(all_cells["eligible_support_set_count"], 0)
        self.assertEqual(unknown["semantic_projection_count"], 2)
        self.assertEqual(unknown["candidate_target_value_group_count"], 4)
        self.assertEqual(unknown["eligible_support_set_count"], 0)
        self.assertFalse(replay["all_value_cell_replay_is_valid_writeback_policy"])
        self.assertFalse(
            replay["previous_informal_six_support_set_interpretation_valid"]
        )

    def test_natural_page_structure_exists_but_target_fairness_is_missing(self) -> None:
        value = target.build_diagnosis(now=0)
        pages = value["frozen_page_structure"]
        unknown = value["baseline_unknown_surface"]
        diagnosis = value["diagnosis"]
        self.assertEqual(pages["page_count"], 70)
        self.assertEqual(pages["page_with_exact_visible_identity_count"], 53)
        self.assertEqual(pages["page_with_founded_or_established_year_count"], 25)
        self.assertEqual(unknown["unknown_cell_count"], 19)
        self.assertEqual(unknown["unknown_cell_count_by_column"], {"Founded": 15, "Country": 4})
        self.assertEqual(
            unknown["unknown_entity_exact_page_source_coverage_histogram"],
            {"0": 3, "1": 8, "2": 4},
        )
        self.assertEqual(
            diagnosis["current_primary_bottleneck"],
            "target_fair_retrieval_reachability_and_same_value_support_conversion_before_unchanged_two_source_gate",
        )
        self.assertFalse(
            diagnosis["target_fair_retrieval_alone_is_sufficient_for_safe_change"]
        )

    def test_authority_and_claims_fail_closed(self) -> None:
        value = target.validate_diagnosis(target.build_diagnosis(now=0))
        self.assertTrue(
            value["authorization"]["append_only_visible_entity_scheduler_implementation"]
        )
        self.assertFalse(
            value["authorization"]["same_population_forward_retry_resume_or_rerun"]
        )
        self.assertFalse(value["authorization"]["fresh_external_protocol_design"])
        self.assertFalse(value["authorization"]["evaluator"])
        self.assertFalse(value["authorization"]["paired_dev64"])
        self.assertFalse(value["authorization"]["exact220"])
        self.assertFalse(value["claim_scope"]["deepwidebench_quality_measured"])
        self.assertFalse(value["claim_scope"]["entropy_or_credit_assignment_validated"])

    def test_resealed_launch_or_support_set_tamper_is_rejected(self) -> None:
        value = target.build_diagnosis(now=0)
        changed = copy.deepcopy(value)
        changed["authorization"]["fresh_external_activation_or_launch"] = True
        changed.pop("diagnosis_payload_sha256")
        changed["diagnosis_payload_sha256"] = target.contract.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_diagnosis(changed)
        changed = copy.deepcopy(value)
        changed["strict_v24365_replay"]["actual_unknown_cells"][
            "eligible_support_set_count"
        ] = 6
        changed.pop("diagnosis_payload_sha256")
        changed["diagnosis_payload_sha256"] = target.contract.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_diagnosis(changed)

    def test_public_artifact_contains_no_runtime_private_surface(self) -> None:
        value = target.build_diagnosis(now=0)
        serialized = json.dumps(value, ensure_ascii=False)
        for task in target.contract.task_vector():
            self.assertNotIn(task["opaque_id"], serialized)
            for entity in target.contract.visible_entities(task["question"]):
                self.assertNotIn(entity, serialized)
        self.assertNotIn("http://", serialized)
        self.assertNotIn("https://", serialized)

    def test_label_blind_source_and_create_only_publication(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        accesses, imports = audit.ast_findings(
            Path("scripts/diagnose_v24769_zero_effect_reachability.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "diagnosis.json"
            target.publish_new(path, {})
            with self.assertRaises(FileExistsError):
                target.publish_new(path, {})


if __name__ == "__main__":
    unittest.main()
