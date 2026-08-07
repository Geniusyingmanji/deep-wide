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

from scripts import preregister_v24784_projection_funnel_external as target  # noqa: E402


class V24784ProjectionFunnelExternalProtocolTests(unittest.TestCase):
    def protocol(self) -> dict:
        return target.build_protocol(
            now=1, require_clean=False, require_pristine=False
        )

    def test_public_parents_and_dependencies_exclude_private_and_consumed_outputs(self) -> None:
        population, audit = target._parents()
        self.assertEqual(population["freshness"]["historical_visible_entity_count"], 4_784)
        self.assertTrue(audit["audit_valid"])
        self.assertFalse(
            audit["source_policy"][
                "v24783_private_population_bytes_opened_parsed_imported_copied_or_hashed"
            ]
        )
        self.assertFalse(
            any(path.parts[:1] in {("evaluation",), ("outputs",)} for path in target.DEPENDENCIES)
        )
        self.assertFalse(
            any("v24780_staged_fallback_external_v1" in str(path) for path in target.DEPENDENCIES)
        )

    def test_visible_task_contract_is_label_blind_and_fixed(self) -> None:
        value = self.protocol()
        task = value["task_contract"]
        self.assertEqual(task["runtime_input_keys"], ["opaque_id", "question"])
        self.assertEqual(task["task_count"], 8)
        self.assertEqual(task["row_count"], 32)
        self.assertFalse(
            task["private_truth_provenance_quality_category_split_or_score_field_present"]
        )

    def test_future_child_order_observes_once_without_effect_or_prediction_change(self) -> None:
        integration = self.protocol()["future_trusted_child_integration"]
        self.assertEqual(integration["implementation_status"], "not_built")
        self.assertEqual(
            integration["ordered_steps"],
            [
                "run_base_runtime_once",
                "fully_validate_base_result_once",
                "read_validated_private_semantic_catalog_inside_same_child_only",
                "build_and_validate_v24781_funnel_at_most_once",
                "emit_base_predictions_plus_fixed_vocabulary_counts_only_receipt",
            ],
        )
        self.assertFalse(integration["absent_or_failed_funnel_fabricates_zero_counts"])
        self.assertFalse(
            integration["base_predictions_or_semantic_projector_changed_by_observer"]
        )
        self.assertEqual(integration["additional_model_search_fetch_or_evaluator_effect"], 0)

    def test_funnel_schema_and_task_local_joint_gate_are_frozen(self) -> None:
        value = self.protocol()
        schema = value["funnel_observation_schema"]
        self.assertEqual(schema["fixed_count_fields"], list(target.funnel.COUNT_FIELDS))
        self.assertEqual(schema["fixed_reason_partition"], list(target.funnel.REASONS))
        gate = value["mechanism_gate_before_private_truth"]
        self.assertEqual(gate["validated_funnel_receipt_count_required"], 8)
        self.assertEqual(
            gate["minimum_task_local_joint_projection_backed_safe_change_task_count"],
            1,
        )
        self.assertFalse(
            gate["cross_task_aggregate_cooccurrence_may_substitute_for_task_local_joint"]
        )
        self.assertFalse(gate["joint_activation_is_causal_or_quality_proof"])

    def test_entropy_quality_benchmark_and_same_population_selection_remain_closed(self) -> None:
        value = self.protocol()
        self.assertFalse(value["entropy_credit_scope"]["credit_assignment_experiment"])
        self.assertFalse(value["entropy_credit_scope"]["projection_count_is_positive_credit"])
        self.assertFalse(value["claim_scope"]["deepwidebench_dev64_or_exact220_score"])
        self.assertFalse(value["claim_scope"]["leaderboard_or_sota"])
        diagnostic = value["diagnostic_scope_if_gate_fails"]
        self.assertFalse(diagnostic["counts_may_select_or_tune_a_same_population_retry"])
        self.assertFalse(diagnostic["failed_or_scored_population_may_be_rerun"])

    def test_authority_stops_at_append_only_integration_build(self) -> None:
        authorization = self.protocol()["authorization"]
        self.assertTrue(authorization["protocol_published"])
        self.assertTrue(authorization["append_only_trusted_child_integration_build"])
        for name in (
            "runner_or_control_plane_build",
            "package_audit_generation",
            "preactivation_audit_generation",
            "activation",
            "execution_start",
            "one_external_forward_launch",
            "quality_or_evaluator_surface_open",
            "paired_dev64",
            "exact220",
            "entropy_or_credit_experiment",
            "leaderboard_or_sota",
        ):
            self.assertFalse(authorization[name])

    def test_resealed_tamper_and_create_only_publication_fail_closed(self) -> None:
        value = self.protocol()
        mutations = (
            lambda item: item["future_trusted_child_integration"].__setitem__(
                "additional_model_search_fetch_or_evaluator_effect", 1
            ),
            lambda item: item["mechanism_gate_before_private_truth"].__setitem__(
                "minimum_task_local_joint_projection_backed_safe_change_task_count",
                0,
            ),
            lambda item: item["authorization"].__setitem__(
                "one_external_forward_launch", True
            ),
        )
        for mutate in mutations:
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
