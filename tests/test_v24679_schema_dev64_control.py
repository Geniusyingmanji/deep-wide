from __future__ import annotations

import copy
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import v24679_schema_dev64_control as control  # noqa: E402


class V24679SchemaDev64ControlTests(unittest.TestCase):
    def test_decision_contract_requires_gain_and_all_metric_nonregression(self) -> None:
        decision = control.DECISION_CONTRACT
        self.assertEqual(decision["minimum_changed_candidate_tasks_for_evaluator_gate"], 1)
        self.assertEqual(decision["minimum_whole_table_success_delta_for_go"], 1)
        for key in (
            "minimum_quality_composite_delta_for_go",
            "minimum_entity_acc_delta_for_go",
            "minimum_f1_by_row_delta_for_go",
            "minimum_f1_by_item_delta_for_go",
            "minimum_column_f1_delta_for_go",
        ):
            self.assertEqual(decision[key], 0.0)
        self.assertEqual(
            decision["maximum_candidate_minus_baseline_runtime_failures_for_go"], 0
        )
        self.assertEqual(
            decision["maximum_candidate_minus_baseline_evaluator_failures_for_go"], 0
        )

    def test_forward_contract_is_label_blind_fixed_denominator(self) -> None:
        value = control.build_forward_contract(
            ROOT, now=0, require_pristine=False, require_clean=False
        )
        self.assertEqual(value["task_contract"]["runtime_boundary"], ["opaque_id", "question"])
        self.assertEqual(value["task_contract"]["selected_count"], 64)
        self.assertEqual(value["execution"]["expected_treated_tasks"], 8)
        self.assertEqual(value["execution"]["total_child_runs"], 72)
        self.assertEqual(
            value["fixed_denominator_contract"][
                "same_run_baseline_exact_reuse_candidate_tasks"
            ],
            56,
        )
        self.assertTrue(value["fixed_denominator_contract"]["failure_as_zero"])
        self.assertFalse(value["authorization"]["activation_or_launch"])
        self.assertFalse(value["authorization"]["evaluator"])

    def test_forward_manifest_excludes_evaluator_capability(self) -> None:
        lowered = "\n".join(control.FORWARD_FILES).casefold()
        for marker in ("official_eval", "evaluator_mapping", "finalize_fullset"):
            self.assertNotIn(marker, lowered)

    def test_protocol_has_postfreeze_evaluator_gate_only(self) -> None:
        protocol = {
            "postfreeze_evaluator_policy": {
                "evaluator_mapping_gold_query_answer_category_split_score_or_reward_opened_or_hashed_pre_freeze": False,
                "separate_evaluator_gate_required_after_both_arm_prediction_freezes": True,
                "changed_candidate_tasks_zero_is_direct_no_go_without_evaluator": True,
            }
        }
        policy = protocol["postfreeze_evaluator_policy"]
        self.assertFalse(
            policy[
                "evaluator_mapping_gold_query_answer_category_split_score_or_reward_opened_or_hashed_pre_freeze"
            ]
        )
        self.assertTrue(
            policy["separate_evaluator_gate_required_after_both_arm_prediction_freezes"]
        )

    def test_parent_requires_build_audit_contract_publication_only(self) -> None:
        value = control._parent(ROOT)
        self.assertTrue(value["authorization"]["forward_contract_publication"])
        self.assertFalse(value["authorization"]["preactivation_or_launch"])

    def test_protocol_validator_rejects_resealed_evaluator_authority(self) -> None:
        fake_forward = {
            "dependency_manifest_sha256": "a" * 64,
        }
        controls = {name: "b" * 64 for name in control.CONTROL_FILES}
        value = {
            "role": "v24679_schema_dev64_preregistration",
            "protocol_id": control.contract.PROTOCOL_ID,
            "forward_contract_sha256": "c" * 64,
            "dependency_manifest_sha256": "a" * 64,
            "control_manifest": controls,
            "control_manifest_sha256": control.contract.payload_sha256(controls),
            "decision_contract": dict(control.DECISION_CONTRACT),
            "task_contract": {
                "selected_per_arm": 64,
                "real_child_runs": 72,
                "failure_as_zero": True,
            },
            "causal_treatment": {
                "untreated_candidate_exactly_reuses_same_run_baseline": True,
            },
            "postfreeze_evaluator_policy": {
                "evaluator_mapping_gold_query_answer_category_split_score_or_reward_opened_or_hashed_pre_freeze": False,
                "separate_evaluator_gate_required_after_both_arm_prediction_freezes": True,
            },
            "authorization": {
                "preactivation_audit_generation": True,
                "single_fresh_paired_dev64_forward_after_activation_and_start": False,
                "evaluator": True,
                "exact220": False,
                "avg_at_4_leaderboard_or_sota": False,
            },
        }
        value["protocol_payload_sha256"] = control.contract.payload_sha256(value)
        with (
            patch.object(control.contract, "validate_forward_contract", return_value=fake_forward),
            patch.object(control.contract, "sha256", return_value="c" * 64),
            patch.object(control, "_manifest", return_value=controls),
        ):
            with self.assertRaises(RuntimeError):
                control.validate_protocol(ROOT, value=value)

    def test_preaudit_resealed_launch_tamper_fails_closed(self) -> None:
        value = {
            "role": "v24679_schema_dev64_preactivation_audit",
            "protocol_id": control.contract.PROTOCOL_ID,
            "audit_valid": True,
            "findings": [],
            "launch_authorized": True,
            "focused_test_count": control.EXPECTED_FOCUSED_TEST_COUNT,
            "forward_contract_sha256": "a" * 64,
            "protocol_sha256": "b" * 64,
            "protected_watchers": [],
            "authorization": {
                "one_fresh_72_child_paired_dev64_forward": True,
                "evaluator": True,
                "exact220": False,
                "leaderboard_or_sota": False,
            },
        }
        value["audit_payload_sha256"] = control.contract.payload_sha256(value)
        with (
            patch.object(control, "_read", return_value=value),
            patch.object(control.contract, "sha256", side_effect=["a" * 64, "b" * 64]),
            patch.object(control.contract, "protected_watcher_snapshot", return_value=[]),
        ):
            with self.assertRaises(RuntimeError):
                control.validate_preaudit(ROOT)

    def test_activation_resealed_wrong_parent_hash_fails_closed(self) -> None:
        value = {
            "role": "v24679_schema_dev64_activation",
            "protocol_id": control.contract.PROTOCOL_ID,
            "status": "active",
            "findings": [],
            "launch_authorized": True,
            "forward_contract_sha256": "a" * 64,
            "protocol_sha256": "b" * 64,
            "preaudit_sha256": "wrong",
            "protected_watchers": [],
            "authorization": {"one_forward_launch": True, "evaluator": False, "exact220": False},
        }
        value["activation_payload_sha256"] = control.contract.payload_sha256(value)
        with (
            patch.object(control, "_read", return_value=value),
            patch.object(
                control.contract,
                "sha256",
                side_effect=["a" * 64, "b" * 64, "c" * 64],
            ),
            patch.object(control.contract, "protected_watcher_snapshot", return_value=[]),
        ):
            with self.assertRaises(RuntimeError):
                control.validate_activation(ROOT)

    def test_execution_start_authorization_is_forward_only(self) -> None:
        expected = {
            "one_fresh_paired_dev64_forward": True,
            "evaluator": False,
            "exact220": False,
        }
        self.assertEqual(expected["one_fresh_paired_dev64_forward"], True)
        self.assertFalse(expected["evaluator"])
        self.assertFalse(expected["exact220"])

    def test_secret_pattern_detects_supported_prefix_without_literal(self) -> None:
        prefix = "tvly" + "-dev-"
        self.assertIsNotNone(control.SECRET.search(prefix + "a" * 20))
        self.assertIsNone(control.SECRET.search("ordinary-placeholder"))


if __name__ == "__main__":
    unittest.main()
