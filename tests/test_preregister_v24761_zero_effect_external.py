from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import preregister_v24761_zero_effect_external as target  # noqa: E402


class V24761ZeroEffectExternalProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_protocol(
            now=0, require_clean=False, require_pristine=False
        )

    def test_parent_population_and_visible_boundary_are_frozen(self) -> None:
        value = self.value
        self.assertTrue(value["parents"]["v24757_audit_valid"])
        self.assertTrue(value["parents"]["v24759_failure_reproduced"])
        self.assertTrue(value["parents"]["v24760_population_fresh"])
        self.assertEqual(value["population"]["fresh_entity_count"], 32)
        self.assertFalse(value["population"]["geographically_balanced_quality_sample"])
        self.assertEqual(value["task_contract"]["runtime_input_keys"], ["opaque_id", "question"])
        self.assertEqual(value["task_contract"]["task_count"], 8)

    def test_manifest_is_tracked_and_evaluator_isolated(self) -> None:
        manifest = self.value["dependency_manifest"]
        self.assertEqual(manifest, target.dependency_manifest())
        self.assertEqual(
            self.value["dependency_manifest_sha256"], target.payload_sha256(manifest)
        )
        for path in manifest:
            for marker in target.FORBIDDEN_DEPENDENCY_MARKERS:
                self.assertNotIn(marker, path.casefold())

    def test_runtime_caps_and_zero_effect_mechanism_gate_are_exact(self) -> None:
        runtime = self.value["runtime"]
        mechanism = self.value["mechanism_gate_before_private_truth"]
        self.assertEqual(runtime["task_executors"], 8)
        self.assertEqual(runtime["global_model_slot_cap"], 8)
        self.assertEqual(runtime["limits"]["model_calls"], 2)
        self.assertEqual(runtime["limits"]["search_queries"], 4)
        self.assertEqual(runtime["limits"]["fetch_targets"], 10)
        self.assertEqual(runtime["adapter_additional_model_query_search_fetch_or_token_effect"], 0)
        self.assertEqual(mechanism["minimum_changed_task_count"], 2)
        self.assertEqual(mechanism["minimum_changed_cell_count"], 4)
        self.assertTrue(mechanism["zero_trigger_stops_without_private_truth_or_quality_read"])

    def test_quality_and_entropy_credit_claims_are_conservative(self) -> None:
        quality = self.value["quality_gate_after_prediction_freeze"]
        credit = self.value["entropy_credit_scope"]
        self.assertEqual(quality["required_exact_table_success_delta"], 1)
        self.assertTrue(quality["candidate_cell_accuracy_nonregression"])
        self.assertTrue(quality["candidate_incorrect_cell_count_nonincrease"])
        self.assertFalse(credit["unknown_reduction_is_positive_credit"])
        self.assertFalse(credit["entropy_drop_is_positive_credit"])
        self.assertFalse(credit["credit_assignment_experiment"])

    def test_publication_has_no_launch_or_quality_authority(self) -> None:
        authorization = self.value["authorization"]
        self.assertTrue(authorization["protocol_published"])
        self.assertTrue(authorization["runner_and_control_plane_build"])
        self.assertFalse(authorization["package_audit_generation"])
        self.assertFalse(authorization["activation"])
        self.assertFalse(authorization["one_external_forward_launch"])
        self.assertFalse(authorization["quality_surface_open"])
        self.assertFalse(authorization["paired_dev64"])
        self.assertFalse(authorization["exact220"])

    def test_resealed_launch_tamper_and_dirty_publication_fail(self) -> None:
        altered = copy.deepcopy(self.value)
        altered["authorization"]["one_external_forward_launch"] = True
        altered.pop("protocol_payload_sha256")
        altered["protocol_payload_sha256"] = target.payload_sha256(altered)
        with self.assertRaises(RuntimeError):
            target.validate_protocol(altered)
        with patch.object(target, "_git", side_effect=["dirty"]):
            with self.assertRaisesRegex(RuntimeError, "clean pushed HEAD"):
                target.build_protocol(
                    now=0, require_clean=True, require_pristine=False
                )


if __name__ == "__main__":
    unittest.main()
