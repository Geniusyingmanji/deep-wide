from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import preregister_v24790_cross_tab_external as target  # noqa: E402


class V24790CrossTabExternalProtocolTests(unittest.TestCase):
    def protocol(self) -> dict:
        return target.build_protocol(now=1, require_clean=False, require_pristine=False)

    def test_public_parents_exclude_private_and_consumed_outputs(self) -> None:
        population, audit = target._parents()
        self.assertEqual(population["freshness"]["historical_visible_entity_count"], 4_816)
        self.assertTrue(audit["audit_valid"])
        self.assertFalse(any(path.parts[:1] in {("evaluation",), ("outputs",)} for path in target.DEPENDENCIES))
        self.assertFalse(any("v24784_projection_funnel_external" in str(path) for path in target.DEPENDENCIES))

    def test_visible_contract_and_effect_envelope_are_fixed(self) -> None:
        value = self.protocol()
        self.assertEqual(value["task_contract"]["runtime_input_keys"], ["opaque_id", "question"])
        self.assertEqual(value["task_contract"]["task_count"], 8)
        envelope = value["base_runtime_effect_envelope"]
        self.assertEqual(envelope["model_calls_per_task"], 2)
        self.assertEqual(envelope["logical_queries_per_task"], 4)
        self.assertEqual(envelope["maximum_physical_fetches_per_task"], 10)

    def test_target_selection_occurs_after_base_and_adds_no_effect(self) -> None:
        integration = self.protocol()["future_trusted_child_integration"]
        self.assertEqual(integration["implementation_status"], "not_built")
        self.assertEqual(integration["maximum_selected_target_per_task"], 1)
        self.assertFalse(integration["target_selection_uses_private_truth_quality_or_evaluator"])
        self.assertFalse(integration["target_selection_changes_acquisition_or_base_predictions"])
        self.assertTrue(integration["same_already_fetched_pages_reused"])
        self.assertEqual(integration["additional_model_search_fetch_or_evaluator_effect"], 0)
        self.assertLess(
            integration["ordered_steps"].index("materialize_base_predictions_without_private_truth"),
            integration["ordered_steps"].index("select_first_baseline_unknown_value_cell_in_canonical_row_major_order"),
        )

    def test_cross_tab_and_strict_joint_gate_are_same_group(self) -> None:
        value = self.protocol()
        schema = value["cross_tab_schema"]
        self.assertEqual(schema["target_count_required_per_valid_receipt"], 1)
        self.assertEqual(schema["unknown_target_count_required_per_valid_receipt"], 1)
        gate = value["mechanism_gate_before_private_truth"]
        self.assertEqual(gate["validated_selected_target_receipt_count_required"], 8)
        self.assertTrue(gate["strict_joint_requires_same_target_value_group"])
        self.assertFalse(gate["cross_task_aggregate_cooccurrence_may_substitute_for_joint"])

    def test_no_target_quality_entropy_and_same_population_retry_remain_closed(self) -> None:
        value = self.protocol()
        self.assertEqual(value["mechanism_gate_before_private_truth"]["no_baseline_unknown_target_count_required"], 0)
        self.assertFalse(value["entropy_credit_scope"]["credit_assignment_experiment"])
        self.assertFalse(value["claim_scope"]["deepwidebench_dev64_or_exact220_score"])
        self.assertFalse(value["diagnostic_scope_if_gate_fails"]["same_population_retry_resume_or_tuning"])

    def test_authority_stops_at_integration_build(self) -> None:
        authorization = self.protocol()["authorization"]
        self.assertTrue(authorization["append_only_trusted_child_integration_build"])
        for name in (
            "runner_or_control_plane_build", "package_audit_generation",
            "preactivation_audit_generation", "activation", "execution_start",
            "one_external_forward_launch", "quality_or_evaluator_surface_open",
            "paired_dev64", "exact220", "entropy_or_credit_experiment",
            "leaderboard_or_sota",
        ):
            self.assertFalse(authorization[name])

    def test_resealed_tamper_and_create_only_fail_closed(self) -> None:
        value = self.protocol()
        for mutate in (
            lambda item: item["future_trusted_child_integration"].__setitem__("maximum_selected_target_per_task", 2),
            lambda item: item["mechanism_gate_before_private_truth"].__setitem__("strict_joint_requires_same_target_value_group", False),
            lambda item: item["authorization"].__setitem__("one_external_forward_launch", True),
        ):
            changed = copy.deepcopy(value)
            mutate(changed)
            changed.pop("protocol_payload_sha256")
            changed["protocol_payload_sha256"] = target.payload_sha256(changed)
            with self.assertRaises(RuntimeError):
                target.validate_protocol(changed)
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "protocol.json"
            target.publish_new(path, {})
            with self.assertRaises(FileExistsError):
                target.publish_new(path, {})


if __name__ == "__main__":
    unittest.main()
