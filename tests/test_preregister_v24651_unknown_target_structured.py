from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import preregister_v24651_unknown_target_structured as prereg


class ProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = prereg.build_protocol(
            now=0, require_clean=False, require_pristine=False
        )

    def test_parent_chain_and_fresh_population_are_bound(self) -> None:
        value = self.value
        self.assertEqual(value["population"]["historical_entity_count"], 4_480)
        self.assertEqual(value["population"]["fresh_entity_count"], 48)
        self.assertEqual(value["population"]["lexicographic_slice_start_inclusive"], 3_000)
        self.assertEqual(value["population"]["lexicographic_slice_stop_exclusive"], 3_482)
        self.assertEqual(value["population"]["literal_and_canonical_overlap_with_history"], 0)
        self.assertTrue(value["parents"]["v24645_population_consumed_and_strict_no_go"])
        self.assertFalse(value["parents"]["v24645_retry_resume_selective_rerun_or_revaluation"])

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

    def test_treatment_budget_and_mechanism_gate_are_frozen(self) -> None:
        mechanism = self.value["mechanism"]
        evaluation = self.value["evaluation_separation"]
        self.assertEqual(mechanism["exact_provider_model_calls_per_valid_task"], 2)
        self.assertEqual(mechanism["hosted_search_query_cap"], 4)
        self.assertEqual(mechanism["generic_fetch_cap"], 6)
        self.assertEqual(mechanism["unknown_target_lookup_cap"], 4)
        self.assertEqual(mechanism["total_fetch_cap"], 10)
        self.assertTrue(mechanism["candidate_consumes_only_new_lookup_projection"])
        self.assertTrue(evaluation["zero_admission_stops_without_gold_or_evaluator"])
        self.assertIn("at_least_one_admitted", evaluation["mechanism_gate_before_gold_open"])

    def test_quality_gate_entropy_scope_and_no_launch_authority(self) -> None:
        evaluation = self.value["evaluation_separation"]
        credit = self.value["entropy_credit_scope"]
        authorization = self.value["authorization"]
        self.assertEqual(evaluation["primary_metric"], "exact_table_successes")
        self.assertIn("strict_candidate_exact_table_gain", evaluation["go_rule"])
        self.assertFalse(credit["zero_intervention_or_zero_outer_utility_receives_positive_task_credit"])
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
