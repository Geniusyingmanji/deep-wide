from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import preregister_v24645_primary_identity_pair as prereg


class ProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = prereg.build_protocol(
            now=0, require_clean=False, require_pristine=False
        )

    def test_parent_chain_and_fresh_population_are_bound(self) -> None:
        value = self.value
        self.assertEqual(value["population"]["historical_entity_count"], 4_432)
        self.assertEqual(value["population"]["fresh_entity_count"], 48)
        self.assertEqual(value["population"]["literal_and_canonical_overlap_with_history"], 0)
        self.assertTrue(value["parents"]["v24642_population_consumed_and_no_go"])
        self.assertFalse(
            value["parents"]["v24642_retry_resume_selective_rerun_or_revaluation"]
        )

    def test_runtime_boundary_and_manifest_are_evaluator_isolated(self) -> None:
        value = self.value
        self.assertEqual(value["task_contract"]["runtime_input_keys"], ["opaque_id", "question"])
        self.assertEqual(value["task_contract"]["selected_tasks"], 12)
        self.assertEqual(value["task_contract"]["selected_arm_predictions"], 24)
        for path in value["dependency_manifest"]:
            for marker in prereg.FORBIDDEN_DEPENDENCY_MARKERS:
                self.assertNotIn(marker, path)
        self.assertEqual(
            value["dependency_manifest_sha256"],
            prereg.payload_sha256(value["dependency_manifest"]),
        )

    def test_identity_gate_and_effect_budget_are_frozen(self) -> None:
        mechanism = self.value["mechanism"]
        self.assertTrue(mechanism["body_only_identity_binding_removed"])
        self.assertTrue(mechanism["search_lead_title_blanked_before_fetch_effect"])
        self.assertTrue(mechanism["ror_profile_lead_rewritten_to_official_api_without_new_effect"])
        self.assertTrue(mechanism["final_fetched_url_used_for_identity_binding"])
        self.assertTrue(mechanism["official_api_url_record_id_and_unique_ror_display_bound"])
        self.assertTrue(mechanism["structured_parse_failure_abstains"])
        self.assertEqual(mechanism["exact_provider_model_calls_per_valid_task"], 2)
        self.assertEqual(self.value["limits"]["search_queries"], 4)
        self.assertEqual(self.value["limits"]["fetch_targets"], 10)

    def test_quality_gate_entropy_scope_and_no_launch_authority(self) -> None:
        evaluation = self.value["evaluation_separation"]
        credit = self.value["entropy_credit_scope"]
        authorization = self.value["authorization"]
        self.assertEqual(evaluation["primary_metric"], "exact_table_successes")
        self.assertIn("strict_candidate_exact_table_gain", evaluation["go_rule"])
        self.assertTrue(credit["primary_identity_binding_precedes_target_value_binding"])
        self.assertTrue(credit["wrong_identity_can_never_receive_positive_task_credit"])
        self.assertFalse(credit["entropy_or_credit_assignment_validated_by_protocol"])
        self.assertTrue(authorization["protocol_published"])
        self.assertFalse(authorization["preactivation_audit"])
        self.assertFalse(authorization["activation"])
        self.assertFalse(authorization["execution_start"])
        self.assertFalse(authorization["one_external_forward_launch"])
        self.assertFalse(authorization["evaluator"])
        self.assertFalse(authorization["dev64"])
        self.assertFalse(authorization["exact220"])

    def test_protocol_seal_and_clean_guard(self) -> None:
        unsigned = dict(self.value)
        seal = unsigned.pop("protocol_sha256")
        self.assertEqual(prereg.payload_sha256(unsigned), seal)
        with patch.object(prereg, "_git", side_effect=["dirty"]):
            with self.assertRaisesRegex(RuntimeError, "clean pushed HEAD"):
                prereg.build_protocol(now=0, require_clean=True, require_pristine=False)


if __name__ == "__main__":
    unittest.main()
