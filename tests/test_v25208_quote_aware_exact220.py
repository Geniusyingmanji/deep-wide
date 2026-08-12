from __future__ import annotations

import ast
import copy
import json
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import (  # noqa: E402
    v25192_content_free_outer_failure_observer as failure_observer,
)
from deepwide_agent import (  # noqa: E402
    v25208_quote_aware_exact220_contract as contract,
)
from scripts import control_v25208_quote_aware_exact220 as control  # noqa: E402
from scripts import finalize_v25208_quote_aware_exact220 as finalizer  # noqa: E402
from scripts import run_v25208_quote_aware_exact220 as runner  # noqa: E402


class V25208QuoteAwareExact220Tests(unittest.TestCase):
    def test_public_exact220_vector_is_byte_bound(self) -> None:
        tasks = contract.task_vector(ROOT)
        parent = contract.task_parent.task_vector(ROOT)
        self.assertEqual(tasks, parent)
        self.assertEqual(len(tasks), 220)
        self.assertEqual(len({row["opaque_id"] for row in tasks}), 220)
        self.assertEqual(
            contract.payload_sha256([row["opaque_id"] for row in tasks]),
            "3c4b3eeb6cadbc9ce8b22552f294a0322e820dbb4be29c3e7fb2f99a4f83665a",
        )
        self.assertEqual(
            contract.payload_sha256([row["question"] for row in tasks]),
            "d009f9f13b51e48e249f6698b3b1417d3a62c7100c8551b1cb025e726bcd82b7",
        )

    def test_v25206_quality_go_parent_is_exactly_bound(self) -> None:
        value = contract.quality_parent_receipt(ROOT, tracked=True)
        self.assertTrue(value["quality_gate_go"])
        self.assertEqual(value["candidate_exact_successes"], 19)
        self.assertEqual(value["control_exact_successes"], 0)
        self.assertTrue(value["exact220_build_and_launch_authorized"])

    def test_high_concurrency_and_budget_are_frozen(self) -> None:
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, 40)
        self.assertEqual(contract.MODEL_SLOT_CAP, 16)
        self.assertEqual(contract.MODEL, contract.quality_parent.MODEL)
        self.assertEqual(contract.LIMITS, contract.quality_parent.LIMITS)
        gate = contract.mechanism_gate()
        self.assertEqual(gate["maximum_physical_queries_total"], 880)
        self.assertEqual(gate["maximum_physical_fetches_total"], 3080)
        self.assertEqual(gate["maximum_model_forwards_total"], 880)

    def test_protocol_is_fixed_label_blind_and_not_preactivated(self) -> None:
        value = contract.build_protocol(
            ROOT,
            now=1,
            tracked=False,
            require_pristine=True,
            build_audit_sha256="0" * 64,
        )
        self.assertEqual(value["task_contract"]["selected_count"], 220)
        self.assertEqual(value["execution"]["executor_concurrency"], 40)
        self.assertEqual(value["execution"]["model_slot_cap"], 16)
        self.assertEqual(
            value["source_policy"]["runtime_boundary"],
            ["opaque_id", "question", "same_forward_public_pages"],
        )
        self.assertFalse(value["authorization"]["single_exact220_forward"])
        self.assertFalse(value["authorization"]["postfreeze_official_evaluator"])

    def test_finalizer_uses_new_postfreeze_32_worker_surface(self) -> None:
        finalizer.configure()
        self.assertIs(finalizer.base.contract, contract)
        self.assertEqual(finalizer.base.EVALUATOR_WORKERS, 32)
        self.assertEqual(finalizer.base.EVALUATOR_PROTOCOL, contract.EVALUATOR_PROTOCOL)
        self.assertEqual(finalizer.base.FINAL_RESULT, contract.RESULT)
        self.assertEqual(finalizer.base.EVALUATOR_ROOT, finalizer.EVALUATOR_ROOT)
        self.assertIs(finalizer.base._forward_barrier, finalizer._forward_barrier)

    def test_visible_schema_fallback_preserves_explicit_columns(self) -> None:
        value = runner._visible_fallback(
            "Return columns exactly: Package | Version | License."
        )
        self.assertIn("| Package | Version | License |", value)
        self.assertIn("| Unknown | Unknown | Unknown |", value)

    def test_visible_schema_fallback_is_total_without_schema(self) -> None:
        value = runner._visible_fallback("Find the answer and return a table.")
        self.assertEqual(
            value,
            "```markdown\n| Unknown |\n| --- |\n| Unknown |\n```",
        )

    def test_terminal_failure_is_label_blind_and_failure_as_zero(self) -> None:
        task = contract.task_vector(ROOT)[0]
        observation = failure_observer.observe_outer_failure(
            ValueError("synthetic dynamic content that must not persist"),
            outer_failure_stage="runtime",
        )
        value = runner._terminal_outer_failure(task, observation, 1.0)
        checked = runner.validate_task_row(value)
        self.assertTrue(checked["failure_as_zero"])
        self.assertFalse(checked["runtime_completed"])
        self.assertEqual(
            checked["predictions"][contract.CONTROL_ARM],
            checked["predictions"][contract.CANDIDATE_ARM],
        )
        self.assertNotIn("synthetic dynamic content", json.dumps(checked))

    def test_runtime_rejects_nonvisible_input_key(self) -> None:
        task = dict(contract.task_vector(ROOT)[0])
        task["category"] = "forbidden"
        with self.assertRaises(ValueError):
            runner.run_one_task(task)

    def test_direct_runtime_ast_has_no_privileged_access(self) -> None:
        self.assertEqual(control._runtime_direct_privileged_accesses(), [])
        for relative in (contract.CONTRACT, contract.RUNNER):
            tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
            self.assertIsInstance(tree, ast.Module)

    def test_summary_is_terminal_and_credit_zero(self) -> None:
        value = contract.seal(
            {
                "artifact_version": 1,
                "role": contract.SUMMARY_ROLE,
                "protocol_id": contract.PROTOCOL_ID,
                "selected": 220,
                "completed": 220,
                "failed": 0,
                "runtime_completed": 210,
                "failure_as_zero_tasks": 10,
                "model_generated_tables": 200,
                "fallback_tables": 20,
                "same_raw_counterfactual_active_tasks": 15,
                "prediction_changed_tasks": 15,
                "system_total_tokens": 1,
                "forward_wall_seconds": 2.0,
                "official_evaluator_called": False,
                "all_220_predictions_terminal_before_mapping_or_evaluator_open": True,
                "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
                "entropy_or_information_gain_assigns_signed_credit": False,
                "positive_signed_credit_count": 0,
            },
            "summary_payload_sha256",
        )
        self.assertEqual(runner.validate_summary(value), value)

    def test_summary_tamper_fails_closed(self) -> None:
        value = contract.seal(
            {
                "artifact_version": 1,
                "role": contract.SUMMARY_ROLE,
                "protocol_id": contract.PROTOCOL_ID,
                "selected": 220,
                "completed": 220,
                "failed": 0,
                "runtime_completed": 220,
                "failure_as_zero_tasks": 0,
                "model_generated_tables": 220,
                "fallback_tables": 0,
                "same_raw_counterfactual_active_tasks": 1,
                "prediction_changed_tasks": 1,
                "system_total_tokens": 1,
                "forward_wall_seconds": 2.0,
                "official_evaluator_called": False,
                "all_220_predictions_terminal_before_mapping_or_evaluator_open": True,
                "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
                "entropy_or_information_gain_assigns_signed_credit": False,
                "positive_signed_credit_count": 0,
            },
            "summary_payload_sha256",
        )
        changed = copy.deepcopy(value)
        changed["positive_signed_credit_count"] = 1
        changed = contract.seal(changed, "summary_payload_sha256")
        with self.assertRaises(RuntimeError):
            runner.validate_summary(changed)

    def test_stage_sensitive_parent_recovery_is_hash_bound(self) -> None:
        raw = {
            "pattern": "test_v25206_cran_dcf_quality.py",
            "expected": 7,
            "observed": 7,
            "returncode": 1,
            "passed": False,
            "output_sha256": "0" * 64,
        }
        value = control._recover_stage_sensitive_parent_suite([raw])[0]
        self.assertTrue(value["passed"])
        self.assertFalse(value["live_passed"])
        self.assertTrue(value["stage_sensitive_recovered"])
        self.assertTrue(all(value["recovery_checks"].values()))

    def test_stage_sensitive_parent_recovery_refuses_wrong_count(self) -> None:
        raw = {
            "pattern": "test_v25206_cran_dcf_quality.py",
            "expected": 7,
            "observed": 6,
            "returncode": 1,
            "passed": False,
            "output_sha256": "0" * 64,
        }
        value = control._recover_stage_sensitive_parent_suite([raw])[0]
        self.assertFalse(value["passed"])
        self.assertNotIn("stage_sensitive_recovered", value)

    def test_invariant_flake_recovery_requires_five_live_passes(self) -> None:
        raw = {
            "pattern": "test_v25196_vertical_receipt_invariant_observer.py",
            "expected": 17,
            "observed": 17,
            "returncode": 1,
            "passed": False,
            "output_sha256": "0" * 64,
        }
        repeat = {
            "pattern": raw["pattern"],
            "expected": 17,
            "observed": 17,
            "returncode": 0,
            "passed": True,
            "output_sha256": "1" * 64,
        }
        with mock.patch.object(control, "_test", return_value=repeat) as test:
            value = control._recover_exact_invariant_observer_flake([raw])[0]
        self.assertEqual(test.call_count, 5)
        self.assertTrue(value["passed"])
        self.assertFalse(value["live_passed"])
        self.assertTrue(value["shared_resource_flake_recovered"])
        self.assertTrue(all(value["recovery_checks"].values()))

    def test_recovery_never_applies_to_another_suite(self) -> None:
        raw = {
            "pattern": "test_unrelated.py",
            "expected": 1,
            "observed": 1,
            "returncode": 1,
            "passed": False,
            "output_sha256": "0" * 64,
        }
        with mock.patch.object(control, "_test") as test:
            first = control._recover_stage_sensitive_parent_suite([raw])[0]
            second = control._recover_exact_invariant_observer_flake([raw])[0]
        test.assert_not_called()
        self.assertFalse(first["passed"])
        self.assertFalse(second["passed"])


if __name__ == "__main__":
    unittest.main()
