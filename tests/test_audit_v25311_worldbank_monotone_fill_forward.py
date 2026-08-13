from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25309_worldbank_monotone_fill_external_contract as contract  # noqa: E402
from scripts import audit_v25311_worldbank_monotone_fill_forward as target  # noqa: E402
from scripts import run_v25309_worldbank_monotone_fill_external as runner  # noqa: E402


class V25311WorldBankMonotoneFillForwardAuditTests(unittest.TestCase):
    def test_expected_forward_surface_is_exact(self) -> None:
        self.assertEqual(len(target.EXPECTED_FORWARD_COMMIT_PATHS), 13)
        self.assertIn(str(contract.ATTEMPT_CLAIM), target.EXPECTED_FORWARD_COMMIT_PATHS)
        self.assertIn(str(contract.FORWARD_RESULT), target.EXPECTED_FORWARD_COMMIT_PATHS)
        self.assertIn(str(contract.PREDICTION_FREEZE), target.EXPECTED_FORWARD_COMMIT_PATHS)
        for index in range(1, 9):
            self.assertIn(
                str(contract.MODEL_SLOT_DIRECTORY / f"slot_{index:02d}.lock"),
                target.EXPECTED_FORWARD_COMMIT_PATHS,
            )

    def test_recursive_key_scan_finds_privileged_content(self) -> None:
        keys = target._recursive_keys(
            {"receipt": [{"question_type": "x"}, {"safe": {"gold": 1}}]}
        )
        self.assertIn("question_type", keys)
        self.assertIn("gold", keys)
        self.assertNotIn("prediction", target._recursive_keys({"safe": 1}))

    def test_forward_commit_boundary_requires_start_then_exact_surface(self) -> None:
        current = "d" * 40
        start_commit = "c" * 40
        start_parent = "b" * 40

        def git(_root: Path, *args: str) -> str:
            if args == ("rev-parse", "target/main"):
                return current
            if args == ("rev-list", "--parents", "-n", "1", current):
                return f"{current} {start_commit}"
            if args == ("diff-tree", "--no-commit-id", "--name-only", "-r", current):
                return "\n".join(target.EXPECTED_FORWARD_COMMIT_PATHS)
            if args == ("rev-parse", f"{current}^"):
                return start_commit
            if args == ("rev-list", "--parents", "-n", "1", start_commit):
                return f"{start_commit} {start_parent}"
            if args == ("diff-tree", "--no-commit-id", "--name-only", "-r", start_commit):
                return str(contract.EXECUTION_START)
            raise AssertionError(args)

        with mock.patch.object(contract, "git", side_effect=git), mock.patch.object(
            target, "_read", return_value={"git_head": start_parent}
        ):
            self.assertTrue(target.forward_commit_boundary(head=current))

    def test_mechanism_decision_binds_evaluator_authority(self) -> None:
        gate = contract.mechanism_gate()
        aggregate = {
            "task_count": 12,
            "terminal_tasks": 12,
            "completed_runtime_tasks": 12,
            "failure_as_zero_tasks": 0,
            "model_generated_tasks": 12,
            "fallback_tasks": 0,
            "parent_two_call_baseline_unknown_tasks": 2,
            "complete_eight_page_prefix_tasks": 2,
            "revision_prompt_within_cap_tasks": 2,
            "third_slot_proposal_tasks": 2,
            "supported_unknown_fill_tasks": 2,
            "supported_unknown_fill_cells": 2,
            "attributable_prediction_change_tasks": 2,
            "query_effect_equal_tasks": 12,
            "fetch_effect_equal_tasks": 12,
            "total_model_calls_at_most_three_tasks": 12,
            "known_cell_schema_row_key_order_or_count_violation_tasks": 0,
            "unsupported_or_conflicting_admitted_fill_cells": 0,
            "physical_queries": gate["maximum_queries_total"],
            "physical_fetches": gate["maximum_fetches_total"],
            "physical_model_forwards": gate["maximum_model_forwards_total"],
            "maximum_queries_on_one_task": 4,
            "maximum_fetches_on_one_task": 10,
            "maximum_model_forwards_on_one_task": 3,
            "model_requests": 36,
            "model_attempts": 36,
            "input_tokens": 1,
            "output_tokens": 1,
            "system_total_tokens": 2,
            "positive_signed_credit_count": 0,
            "batch_wall_seconds": 1.0,
            "contains_question_query_url_page_value_answer_prediction_or_credential": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
            "evaluator_or_quality_metric_called": False,
        }
        self.assertTrue(runner.mechanism_decision(aggregate)["postfreeze_evaluator_after_pushed_forward_audit"])
        changed = copy.deepcopy(aggregate)
        changed["supported_unknown_fill_tasks"] = 1
        changed["supported_unknown_fill_cells"] = 1
        changed["attributable_prediction_change_tasks"] = 1
        self.assertFalse(runner.mechanism_decision(changed)["postfreeze_evaluator_after_pushed_forward_audit"])

    def test_invalid_or_tampered_audit_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            target.validate_audit({})


if __name__ == "__main__":
    unittest.main()
