from __future__ import annotations

import copy
import hashlib
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25423_list_atomic_shared_effect_external_contract as contract  # noqa: E402
from scripts import run_v25423_list_atomic_shared_effect_external as target  # noqa: E402


def table(identity="RFC 9720", authors="A. Smith; B. Jones") -> str:
    return (
        "```markdown\n"
        "| RFC | Title | Authors | Status | Stream | Published |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        f"| {identity} | Title | {authors} | Informational | IETF | May 2024 |\n"
        "```"
    )


def completed_row(index: int) -> dict:
    task = contract.task_vector()[index]
    base = table(f"RFC {9720 + index * 4}")
    raw = table(
        f"RFC {9720 + index * 4}",
        "A. Smith Example Corp B. Jones Other Corp",
    )
    predictions = {
        "shared_base_table": base,
        "raw_changed_safe_candidate": raw,
        "guarded_candidate": base,
    }
    effects = {
        "query_admitted_count": 4,
        "fetch_admitted_count": 10,
        "model_admitted_count": 3,
        "query_rejected_count": 0,
        "fetch_rejected_count": 0,
        "model_rejected_count": 0,
    }
    cost = {
        "model": {
            "requests": 3,
            "attempts": 3,
            "input_tokens": 10,
            "output_tokens": 5,
            "total_tokens": 15,
        },
        "search": {
            phase: {
                "calls": 2,
                "failures": 0,
                "tool_calls": 2,
                "fetch_calls": 5,
                "fetch_failures": 0,
                "input_tokens": 2,
                "output_tokens": 3,
                "total_tokens": 5,
            }
            for phase in contract.PHASES
        },
        "system_total_tokens": 25,
    }
    value = {
        "artifact_version": 1,
        "role": target.TASK_ROLE,
        "protocol_id": contract.PROTOCOL_ID,
        "opaque_id": task["opaque_id"],
        "task_index": index,
        "runtime_input_keys": ["opaque_id", "question", "same_forward_public_pages"],
        "terminal": True,
        "runtime_completed": True,
        "failure_as_zero": False,
        "outer_failure_type": None,
        "runtime_result": {"mock": True},
        "runtime_result_payload_sha256": "a" * 64,
        "predictions": predictions,
        "prediction_sha256": {
            arm: hashlib.sha256(prediction.encode()).hexdigest()
            for arm, prediction in predictions.items()
        },
        "prediction_kind": "model_generated",
        "raw_candidate_changed": True,
        "guarded_candidate_changed_from_base": False,
        "guard_changed_raw_candidate": True,
        "changed_coordinate_count": 1,
        "list_semantic_changed_coordinate_count": 1,
        "retained_candidate_coordinate_count": 0,
        "rejected_list_cardinality_decrease_count": 1,
        "content_free_stage_receipt": {"mock": True},
        "actual_effect_snapshot": effects,
        "cost": cost,
        "hard_failure_health": target._health(),
        "elapsed_seconds": 1.0,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
        "query_url_title_page_quote_record_field_value_answer_or_credential_persisted_outside_sealed_runtime_and_predictions": False,
    }
    return contract.seal(value, "result_payload_sha256")


def decoded(row: dict) -> dict:
    guard = {
        "changed_coordinate_count": 1,
        "list_semantic_changed_coordinate_count": 1,
        "retained_candidate_coordinate_count": 0,
        "rejected_list_cardinality_decrease_count": 1,
        "guard_changed_candidate": True,
    }
    parent = {
        "physical_query_count": 4,
        "physical_fetch_count": 10,
        "physical_model_forward_count": 3,
        "system_total_tokens": 25,
        "first_wave_completed": True,
        "second_wave_completed": True,
        "grounded_plan_model_call_success": True,
        "base_synthesis_model_success": True,
        "base_table_exact_canonical": True,
    }
    budget = {
        "query_admitted_count": 4,
        "fetch_admitted_count": 10,
        "model_admitted_count": 3,
        "query_rejected_count": 0,
        "fetch_rejected_count": 0,
        "model_rejected_count": 0,
    }
    return {
        "result": {
            "role": target.runtime.ROLE,
            "opaque_id": row["opaque_id"],
            "result_payload_sha256": "a" * 64,
            "prediction_kind": "model_generated",
            "raw_candidate_changed": True,
            "guarded_prediction_changed_from_base": False,
            "cost": row["cost"],
        },
        "stage": row["content_free_stage_receipt"],
        "parent_receipt": parent,
        "guard_receipt": guard,
        "budget": budget,
        "predictions": row["predictions"],
    }


class V25423ListAtomicSharedEffectExternalTests(unittest.TestCase):
    def test_contract_population_execution_and_quality_are_fixed(self) -> None:
        self.assertEqual(len(contract.task_vector()), 20)
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, 20)
        self.assertEqual(contract.LIMITS["search_queries"], 4)
        self.assertEqual(contract.LIMITS["model_calls"], 3)
        self.assertTrue(contract.quality_gate()["base_raw_and_guarded_share_one_parent_forward"])
        self.assertFalse(
            contract.source_policy()[
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
            ]
        )

    def test_fallback_has_all_three_equal_tables_and_failure_as_zero(self) -> None:
        task = contract.task_vector()[0]
        row = target._terminal_outer_failure(
            task, ValueError("x"), 1.0, budget=None, health=None
        )
        self.assertFalse(row["runtime_completed"])
        self.assertTrue(row["failure_as_zero"])
        self.assertEqual(len(set(row["predictions"].values())), 1)
        self.assertEqual(row["changed_coordinate_count"], 0)

    def test_completed_row_replays_three_predictions_and_guard_counts(self) -> None:
        row = completed_row(0)
        with mock.patch.object(target, "_decode_completed", return_value=decoded(row)):
            self.assertEqual(target.validate_task_row(row), row)
            changed = copy.deepcopy(row)
            changed["predictions"]["guarded_candidate"] = changed["predictions"][
                "raw_changed_safe_candidate"
            ]
            changed["prediction_sha256"]["guarded_candidate"] = hashlib.sha256(
                changed["predictions"]["guarded_candidate"].encode()
            ).hexdigest()
            changed["guard_changed_raw_candidate"] = False
            changed.pop("result_payload_sha256")
            changed = contract.seal(changed, "result_payload_sha256")
            with self.assertRaises(ValueError):
                target.validate_task_row(changed)

    def test_aggregate_and_mechanism_gate_pass_for_exact_twenty(self) -> None:
        rows = [completed_row(index) for index in range(20)]
        mapping = {row["opaque_id"]: decoded(row) for row in rows}
        with mock.patch.object(
            target,
            "_decode_completed",
            side_effect=lambda result, stage: mapping[next(
                row["opaque_id"] for row in rows if row["runtime_result"] is result
            )],
        ):
            # Identity comparison above is brittle after deepcopy in validation;
            # validate in fixed call order instead.
            pass
        queue = [decoded(row) for row in rows]
        with mock.patch.object(target, "_decode_completed", side_effect=queue * 3):
            aggregate = target.aggregate_rows(rows, wall_seconds=2.0)
            decision = target.mechanism_decision(aggregate)
        self.assertTrue(decision["mechanism_gate_passed"])
        self.assertEqual(aggregate["completed_physical_queries"], 80)
        self.assertEqual(aggregate["rejected_list_cardinality_decrease_count"], 20)

    def test_any_failure_keeps_fixed_denominator_but_gate_is_no_go(self) -> None:
        rows = [completed_row(index) for index in range(19)]
        rows.append(
            target._terminal_outer_failure(
                contract.task_vector()[19], RuntimeError("x"), 1.0, budget=None, health=None
            )
        )
        queue = [decoded(row) for row in rows[:19]]
        with mock.patch.object(target, "_decode_completed", side_effect=queue * 3):
            aggregate = target.aggregate_rows(rows, wall_seconds=2.0)
            decision = target.mechanism_decision(aggregate)
        self.assertEqual(aggregate["terminal_tasks"], 20)
        self.assertFalse(decision["mechanism_gate_passed"])

    def test_forward_result_is_sealed_and_never_authorizes_quality_directly(self) -> None:
        aggregate = {
            **{name: 0 for name in target.AGGREGATE_INTEGER_FIELDS},
            "task_count": 20,
            "terminal_tasks": 20,
            "failure_as_zero_tasks": 20,
            "outer_failure_tasks": 20,
            "naked_outer_failure_tasks": 20,
            "per_task_hard_cap_preserved_tasks": 20,
            "batch_wall_seconds": 1.0,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
            "question_prediction_query_url_page_record_value_or_credential_persisted_in_aggregate": False,
        }
        aggregate = target.validate_aggregate(aggregate)
        value = contract.seal(
            {
                "artifact_version": 1,
                "role": target.FORWARD_ROLE,
                "protocol_id": contract.PROTOCOL_ID,
                "aggregate": aggregate,
                "mechanism_decision": target.mechanism_decision(aggregate),
                "authorization": {
                    "forward_audit": True,
                    "postfreeze_quality_protocol": False,
                    "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
                    "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
                },
            },
            "result_payload_sha256",
        )
        self.assertEqual(target.validate_forward_result(value), value)

    def test_forward_dependency_closure_excludes_evaluator_and_diagnosis(self) -> None:
        paths = {str(path) for path in contract.forward_dependency_closure(ROOT)}
        self.assertFalse(any("evaluate_v254" in path for path in paths))
        self.assertFalse(any("diagnose_v25419" in path for path in paths))

    def test_runtime_input_boundary_is_exactly_visible_task_and_clients(self) -> None:
        task = contract.task_vector()[0]
        self.assertEqual(set(task), {"opaque_id", "question"})
        with self.assertRaises(ValueError):
            target.run_one_task({**task, "category": "forbidden"})


if __name__ == "__main__":
    unittest.main()
