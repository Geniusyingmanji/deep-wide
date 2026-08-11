from __future__ import annotations

import ast
import copy
import hashlib
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25103_complete_column_external_contract as contract  # noqa: E402
from scripts import run_v25103_complete_column_external as runner  # noqa: E402


def completed_row(index: int = 0, *, exposed: bool = True, changed: bool = True) -> dict:
    control = "| Package | Latest version | Latest release date (YYYY-MM-DD) | Requires-Python |\n|---|---|---|---|\n| x | 1 | 2026-01-01 | >=3.10 |"
    candidate = control + (" " if changed else "")
    receipt = {
        "planned_query_count": 4,
        "physical_query_count": 4,
        "physical_fetch_count": 10,
        "usable_page_count": 8,
        "physical_model_logical_call_count": 4,
        "model_provider_request_count": 4,
        "model_provider_attempt_count": 4,
        "control_evidence_characters": 1000,
        "candidate_evidence_characters": 1000,
        "arm_metrics": {
            arm: {
                "effective_model_logical_call_count": 3,
                "model_success": True,
            }
            for arm in contract.ARMS
        },
        "candidate_evidence_changed": exposed,
        "prediction_changed": changed,
        "representation_validation_failed": False,
    }
    runtime_result = {
        "status": "terminal",
        "opaque_id": contract.task_vector()[index]["opaque_id"],
        "model_success": {arm: True for arm in contract.ARMS},
        "normalizer_status": {arm: "exact" for arm in contract.ARMS},
        "predictions": {contract.CONTROL_ARM: control, contract.CANDIDATE_ARM: candidate},
        "prediction_sha256": {
            contract.CONTROL_ARM: hashlib.sha256(control.encode()).hexdigest(),
            contract.CANDIDATE_ARM: hashlib.sha256(candidate.encode()).hexdigest(),
        },
        "prediction_changed": changed,
        "candidate_evidence_changed": exposed,
        "content_free_receipt": receipt,
        "cost": {"system_total_tokens": 10},
        "failure_types": {contract.CONTROL_ARM: None, contract.CANDIDATE_ARM: None},
        "elapsed_seconds": 1.0,
    }
    with mock.patch.object(runner.runtime, "validate_result", return_value=runtime_result):
        return runner._from_runtime(
            contract.task_vector()[index],
            contract.arm_order_vector()[index],
            runtime_result,
            runner._health({"query_local_mapping_failure_rows": 2}),
        )


class V25103CompleteColumnExternalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = [
            completed_row(index, exposed=index < 8, changed=index < 4)
            for index in range(contract.TASK_COUNT)
        ]

    def test_fresh_visible_population_and_balanced_order(self) -> None:
        tasks = contract.task_vector()
        self.assertEqual(len(tasks), 20)
        self.assertEqual(len({row["opaque_id"] for row in tasks}), 20)
        self.assertTrue(all(set(row) == {"opaque_id", "question"} for row in tasks))
        self.assertTrue(all("PyPI as the visible authority" in row["question"] for row in tasks))
        self.assertEqual(sum(order[0] == contract.CANDIDATE_ARM for order in contract.arm_order_vector()), 10)

    def test_source_policy_separates_mapping_from_terminal_failure(self) -> None:
        policy = contract.source_policy()
        self.assertTrue(policy["query_local_mapping_failure_is_coverage_diagnostic_not_terminal_transport_failure"])
        self.assertTrue(policy["terminal_hard_failure_uses_transport_timeout_helper_or_model_effect_receipts_only"])
        self.assertTrue(policy["prediction_change_counts_only_when_candidate_evidence_changed"])
        self.assertTrue(
            policy[
                "every_non_key_column_requires_one_ordered_found_or_unavailable_disposition"
            ]
        )
        self.assertTrue(
            policy[
                "post_synthesis_accounting_or_receipt_validation_failure_is_terminal_no_go"
            ]
        )
        self.assertFalse(policy["entropy_or_information_gain_assigns_signed_credit"])

    def test_task_wrapper_is_content_free_and_valid(self) -> None:
        row = self.rows[0]
        with mock.patch.object(runner.runtime, "validate_receipt", return_value=row["content_free_receipt"]):
            checked = runner.validate_task_row(row)
        self.assertTrue(checked["runtime_completed"])
        self.assertEqual(checked["effect_health"]["query_local_mapping_failure_rows"], 2)

    def test_mechanism_gate_allows_mapping_diagnostic_but_not_terminal_failure(self) -> None:
        with mock.patch.object(runner.runtime, "validate_receipt", side_effect=lambda value: value):
            aggregate = runner.aggregate_rows(self.rows, wall_seconds=1.0)
        self.assertEqual(aggregate["query_local_mapping_failure_rows"], 40)
        self.assertTrue(runner.mechanism_decision(aggregate)["mechanism_gate_passed"])
        changed = copy.deepcopy(aggregate)
        changed["terminal_transport_timeout_helper_or_model_hard_failures"] = 1
        self.assertFalse(runner.mechanism_decision(changed)["mechanism_gate_passed"])

    def test_gate_requires_exposure_prediction_change_and_exact_budgets(self) -> None:
        with mock.patch.object(runner.runtime, "validate_receipt", side_effect=lambda value: value):
            aggregate = runner.aggregate_rows(self.rows, wall_seconds=1.0)
        for name in (
            "verifier_exposure_tasks",
            "prediction_changed_tasks",
            "exposed_and_prediction_changed_tasks",
            "physical_queries",
        ):
            changed = copy.deepcopy(aggregate)
            changed[name] -= 1
            with self.subTest(name=name):
                self.assertFalse(runner.mechanism_decision(changed)["mechanism_gate_passed"])

    def test_unexposed_prediction_change_cannot_pass_separate_thresholds(self) -> None:
        rows = [
            completed_row(
                index,
                exposed=index < 8,
                changed=4 <= index < 8,
            )
            for index in range(contract.TASK_COUNT)
        ]
        with mock.patch.object(runner.runtime, "validate_receipt", side_effect=lambda value: value):
            aggregate = runner.aggregate_rows(rows, wall_seconds=1.0)
        self.assertEqual(aggregate["verifier_exposure_tasks"], 8)
        self.assertEqual(aggregate["prediction_changed_tasks"], 4)
        self.assertEqual(aggregate["exposed_and_prediction_changed_tasks"], 4)
        self.assertEqual(aggregate["unexposed_and_prediction_changed_tasks"], 0)
        self.assertTrue(runner.mechanism_decision(aggregate)["mechanism_gate_passed"])
        changed = copy.deepcopy(aggregate)
        changed["exposed_and_prediction_changed_tasks"] = 0
        changed["unexposed_and_prediction_changed_tasks"] = 4
        self.assertFalse(runner.mechanism_decision(changed)["mechanism_gate_passed"])

    def test_completed_row_rejects_unexposed_prediction_change(self) -> None:
        row = completed_row(0, exposed=False, changed=True)
        with mock.patch.object(runner.runtime, "validate_receipt", side_effect=lambda value: value):
            with self.assertRaises(RuntimeError):
                runner.validate_task_row(row)

    def test_representation_failure_is_counted_and_cannot_pass(self) -> None:
        with mock.patch.object(runner.runtime, "validate_receipt", side_effect=lambda value: value):
            aggregate = runner.aggregate_rows(self.rows, wall_seconds=1.0)
        changed = copy.deepcopy(aggregate)
        changed["representation_validation_failure_tasks"] = 1
        self.assertFalse(runner.mechanism_decision(changed)["mechanism_gate_passed"])

    def test_failure_as_zero_is_terminal_and_cannot_pass(self) -> None:
        failure = runner._terminal_outer_failure(
            contract.task_vector()[0],
            contract.arm_order_vector()[0],
            ValueError("x"),
            1.0,
            runner._health(),
        )
        self.assertTrue(runner.validate_task_row(failure)["failure_as_zero"])
        rows = [failure, *self.rows[1:]]
        with mock.patch.object(runner.runtime, "validate_receipt", side_effect=lambda value: value):
            aggregate = runner.aggregate_rows(rows, wall_seconds=1.0)
        self.assertFalse(runner.mechanism_decision(aggregate)["mechanism_gate_passed"])

    def test_accounting_failure_receipt_is_preserved_and_cannot_pass(self) -> None:
        fallback = runner._fallback_table()
        runtime_result = {
            "opaque_id": contract.task_vector()[0]["opaque_id"],
            "status": "terminal_accounting_failure",
            "model_success": {arm: False for arm in contract.ARMS},
            "normalizer_status": {arm: "not_attempted" for arm in contract.ARMS},
            "predictions": {arm: fallback for arm in contract.ARMS},
            "prediction_sha256": {
                arm: hashlib.sha256(fallback.encode()).hexdigest()
                for arm in contract.ARMS
            },
            "prediction_changed": False,
            "candidate_evidence_changed": False,
            "content_free_receipt": {
                "failure_stage": "post_synthesis_accounting",
                "failure_type": "ValueError",
            },
            "cost": None,
            "failure_types": None,
            "elapsed_seconds": 1.0,
        }
        with mock.patch.object(
            runner.runtime, "validate_result", return_value=runtime_result
        ), mock.patch.object(
            runner.runtime,
            "validate_accounting_failure_receipt",
            side_effect=lambda value: value,
        ):
            row = runner._from_runtime(
                contract.task_vector()[0],
                contract.arm_order_vector()[0],
                runtime_result,
                runner._health(),
            )
            checked = runner.validate_task_row(row)
        self.assertTrue(checked["failure_as_zero"])
        self.assertFalse(checked["runtime_completed"])
        self.assertIsNone(checked["outer_failure_type"])
        self.assertTrue(
            checked["post_synthesis_accounting_or_receipt_validation_failed"]
        )
        rows = [checked, *self.rows[1:]]
        with mock.patch.object(
            runner.runtime, "validate_receipt", side_effect=lambda value: value
        ), mock.patch.object(
            runner.runtime,
            "validate_accounting_failure_receipt",
            side_effect=lambda value: value,
        ):
            aggregate = runner.aggregate_rows(rows, wall_seconds=1.0)
        self.assertEqual(
            aggregate[
                "post_synthesis_accounting_or_receipt_validation_failure_tasks"
            ],
            1,
        )
        self.assertEqual(aggregate["outer_hard_failures"], 0)
        self.assertFalse(runner.mechanism_decision(aggregate)["mechanism_gate_passed"])

    def test_extra_privileged_key_fails_closed(self) -> None:
        for key in ("category", "question_type", "gold", "score", "reward"):
            changed = copy.deepcopy(self.rows[0])
            changed[key] = "forbidden"
            changed.pop("result_payload_sha256")
            changed = contract.seal(changed, "result_payload_sha256")
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                runner.validate_task_row(changed)

    def test_forward_sources_label_blind_and_evaluator_absent(self) -> None:
        forbidden = {"category", "question_type", "ground_truth", "answer_key", "gold", "score", "reward"}
        accesses: list[str] = []
        for relative in (
            contract.RUNNER,
            Path("src/deepwide_agent/v25101_complete_column_value_shape_paired_runtime.py"),
        ):
            tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                    if node.slice.value in forbidden:
                        accesses.append(str(node.slice.value))
        self.assertEqual(accesses, [])
        self.assertFalse((ROOT / contract.EVALUATOR).exists())


if __name__ == "__main__":
    unittest.main()
