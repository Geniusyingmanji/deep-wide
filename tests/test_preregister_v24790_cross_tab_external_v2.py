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

from scripts import preregister_v24790_cross_tab_external_v2 as target  # noqa: E402


class V24790CrossTabExternalV2ProtocolTests(unittest.TestCase):
    def protocol(self) -> dict:
        return target.build_protocol(now=1, require_clean=False, require_pristine=False)

    def test_v1_is_valid_but_unimplemented_and_revoked(self) -> None:
        prior = target._v1()
        self.assertTrue(prior["authorization"]["append_only_trusted_child_integration_build"])
        value = self.protocol()
        self.assertFalse(value["authorization"]["v1_integration_build"])
        self.assertTrue(value["parent_v1"]["integration_build_authority_revoked_before_implementation"])
        self.assertFalse(value["parent_v1"]["runner_lease_model_search_fetch_or_forward_effect_before_revocation"])

    def test_correction_preserves_all_entity_segment_boundaries(self) -> None:
        value = self.protocol()
        defect = value["v1_defect"]
        self.assertFalse(defect["one_target_catalog_rebuild_allowed"])
        self.assertTrue(defect["full_target_catalog_required_for_segment_replay"])
        self.assertTrue(defect["other_visible_entities_continue_to_delimit_selected_target_segments"])
        self.assertTrue(defect["adjacent_entity_relation_may_be_rebound_if_boundaries_are_removed"])

    def test_corrected_integration_filters_without_catalog_or_prediction_mutation(self) -> None:
        integration = self.protocol()["corrected_future_integration"]
        self.assertEqual(integration["implementation_status"], "not_built")
        self.assertFalse(integration["full_target_catalog_or_original_projection_vector_mutated"])
        self.assertFalse(integration["single_target_catalog_rebuilt"])
        self.assertEqual(integration["maximum_selected_target_per_task"], 1)
        self.assertEqual(integration["additional_model_search_fetch_or_evaluator_effect"], 0)
        self.assertFalse(integration["prediction_bytes_changed_by_observer"])

    def test_selected_receipt_freezes_same_group_joint(self) -> None:
        receipt = self.protocol()["selected_target_receipt_contract"]
        self.assertEqual(receipt["target_count"], 1)
        self.assertEqual(receipt["unknown_target_count"], 1)
        self.assertTrue(receipt["target_and_group_partitions_exact"])
        self.assertTrue(receipt["strict_joint_requires_same_selected_target_value_group"])
        self.assertFalse(receipt["cross_task_or_cross_group_margins_used_as_joint"])

    def test_dependency_and_source_policy_exclude_private_surfaces(self) -> None:
        value = self.protocol()
        self.assertFalse(any(path.parts[:1] in {("evaluation",), ("outputs",)} for path in target.DEPENDENCIES))
        self.assertFalse(value["source_policy"]["v24789_private_population_truth_provenance_or_quality_opened_or_hashed"])
        self.assertFalse(value["source_policy"]["v24784_output_prediction_task_result_page_or_visible_task_opened_or_hashed"])

    def test_authority_stops_at_corrected_integration_build(self) -> None:
        authorization = self.protocol()["authorization"]
        self.assertTrue(authorization["append_only_full_catalog_selected_target_integration_build"])
        for name in (
            "runner_or_control_plane_build", "package_audit_generation",
            "preactivation_audit_generation", "activation", "execution_start",
            "one_external_forward_launch", "quality_or_evaluator_surface_open",
            "paired_dev64", "exact220", "entropy_or_credit_experiment",
            "leaderboard_or_sota",
        ):
            self.assertFalse(authorization[name])

    def test_resealed_rebuild_or_launch_tamper_and_create_only_fail(self) -> None:
        value = self.protocol()
        for mutate in (
            lambda item: item["v1_defect"].__setitem__("one_target_catalog_rebuild_allowed", True),
            lambda item: item["corrected_future_integration"].__setitem__("single_target_catalog_rebuilt", True),
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
