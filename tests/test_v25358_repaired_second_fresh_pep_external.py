from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25358_repaired_second_fresh_pep_external_contract as contract  # noqa: E402
from scripts import run_v25353_fresh_pep_grounded_fact_external as old_runner  # noqa: E402
from scripts import run_v25358_repaired_second_fresh_pep_external as runner  # noqa: E402
import test_v25353_fresh_pep_grounded_fact_external as old_fixture  # noqa: E402


def _stage(parent_sha256: str) -> dict:
    value = {
        "artifact_version": 1,
        "role": runner.runtime.STAGE_RECEIPT_ROLE,
        "policy_id": runner.runtime.POLICY_ID,
        "parent_role": runner.runtime.parent.ROLE,
        "parent_policy_id": runner.runtime.parent.POLICY_ID,
        "parent_result_payload_sha256": parent_sha256,
        "logical_model_call_count": 4,
        "input_provider_query_string_count": 4,
        "compatible_provider_query_seed_count": 4,
        "transformed_or_rejected_provider_query_count": 0,
        "emitted_query_seed_count": 4,
        "plan_model_effect_failed": False,
        "plan_model_effect_failure_type": None,
        "plan_transport_failed": False,
        "plan_output_validation_failed": False,
        "plan_output_validation_failure_type": None,
        "visible_fallback_query_seed_used": False,
        "query_projection_completed_before_first_search_or_fetch_effect": True,
        "frozen_v25123_visible_query_projector_reused": True,
        "markup_urls_controls_and_forbidden_syntax_removed": True,
        "completed_four_query_vector_valid_under_downstream_grammar": True,
        "grounded_plan_fact_treatment_and_attribution_rule_unchanged": True,
        "physical_query_fetch_model_caps_unchanged": True,
        "additional_model_search_fetch_token_context_wall_or_network_budget": False,
        "contains_question_query_column_url_title_page_prediction_answer_hash_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = contract.payload_sha256(value)
    return runner.runtime.validate_stage_receipt(value)


def completed_row(index: int, *, exposed: bool) -> dict:
    old = old_fixture.completed_row(index, exposed=exposed)
    old["opaque_id"] = contract.task_vector()[index]["opaque_id"]
    old["arm_order"] = contract.arm_order_vector()[index]
    old.pop("result_payload_sha256")
    parent = {
        "artifact_version": 1,
        "role": runner.runtime.parent.ROLE,
        "policy_id": runner.runtime.parent.POLICY_ID,
        "opaque_id": old["opaque_id"],
        "status": "terminal",
        "predictions": copy.deepcopy(old["predictions"]),
        "prediction_sha256": copy.deepcopy(old["prediction_sha256"]),
        "model_success": copy.deepcopy(old["model_success"]),
        "normalizer_status": copy.deepcopy(old["normalizer_status"]),
        "failure_types": copy.deepcopy(old["failure_types"]),
        "prediction_changed": old["prediction_changed"],
        "candidate_production_prompt_changed": old[
            "candidate_production_prompt_changed"
        ],
        "attributable_prediction_change": old["attributable_prediction_change"],
        "unattributable_prediction_change": old[
            "unattributable_prediction_change"
        ],
        "elapsed_seconds": old["elapsed_seconds"],
        "cost": copy.deepcopy(old["cost"]),
        "content_free_receipt": copy.deepcopy(old["content_free_receipt"]),
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    parent["result_payload_sha256"] = contract.payload_sha256(parent)
    runner.runtime.validate_parent_result(parent)
    old["role"] = "v25358_repaired_second_fresh_pep_task_result"
    old["protocol_id"] = contract.PROTOCOL_ID
    old["pre_effect_query_contract_receipt"] = _stage(
        parent["result_payload_sha256"]
    )
    old["result_payload_sha256"] = contract.payload_sha256(old)
    return runner.validate_task_row(old)


def failure_row(index: int) -> dict:
    return runner._terminal_outer_failure(
        contract.task_vector()[index],
        contract.arm_order_vector()[index],
        RuntimeError("synthetic"),
        1.0,
        budget=None,
        health=runner._health(),
    )


class V25358RepairedSecondFreshPepExternalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.completed = [
            completed_row(index, exposed=index < 12)
            for index in range(contract.TASK_COUNT)
        ]

    def test_protocol_population_is_fresh_balanced_and_pre_effect_repaired(self) -> None:
        self.assertEqual(len(contract.task_vector()), contract.TASK_COUNT)
        self.assertEqual(
            contract.payload_sha256(contract.arm_order_vector()),
            contract.population.EXPECTED_ARM_ORDER_VECTOR_SHA256,
        )
        self.assertEqual(
            sum(
                order[0] == contract.CANDIDATE_ARM
                for order in contract.arm_order_vector()
            ),
            10,
        )
        self.assertTrue(
            contract.source_policy()[
                "pre_effect_query_projection_required_before_first_search_or_fetch"
            ]
        )

    def test_completed_row_validates_parent_and_repair_receipt_binding(self) -> None:
        row = runner.validate_task_row(self.completed[0])
        self.assertTrue(row["runtime_completed"])
        self.assertEqual(
            row["actual_effect_snapshot"]["query_admitted_count"], 4
        )
        self.assertEqual(
            row["actual_effect_snapshot"]["model_admitted_count"], 4
        )
        stage = runner.runtime.validate_stage_receipt(
            row["pre_effect_query_contract_receipt"]
        )
        self.assertTrue(
            stage["query_projection_completed_before_first_search_or_fetch_effect"]
        )

    def test_gate_go_consistently_allows_two_terminal_failure_as_zero_rows(self) -> None:
        rows = [*self.completed[:18], failure_row(18), failure_row(19)]
        aggregate = runner.aggregate_rows(rows, wall_seconds=1.0)
        decision = runner.mechanism_decision(aggregate)
        self.assertEqual(aggregate["completed_runtime_tasks"], 18)
        self.assertEqual(aggregate["failure_as_zero_tasks"], 2)
        self.assertEqual(aggregate["outer_failure_tasks"], 2)
        self.assertTrue(decision["mechanism_gate_passed"])
        self.assertTrue(decision["deepwidebench_successor_build_authorized"])

    def test_gate_rejects_third_failure_budget_or_unrecoverable_failure(self) -> None:
        rows = [*self.completed[:17], failure_row(17), failure_row(18), failure_row(19)]
        aggregate = runner.aggregate_rows(rows, wall_seconds=1.0)
        self.assertFalse(runner.mechanism_decision(aggregate)["mechanism_gate_passed"])
        base = runner.aggregate_rows(self.completed, wall_seconds=1.0)
        for field, value in (
            ("budget_rejection_tasks", 1),
            ("unrecoverable_hard_failure_tasks", 3),
            ("completed_physical_queries", base["completed_physical_queries"] - 1),
            (
                "completed_physical_model_forwards",
                base["completed_physical_model_forwards"] - 1,
            ),
        ):
            changed = copy.deepcopy(base)
            changed[field] = value
            with self.subTest(field=field):
                self.assertFalse(
                    runner.mechanism_decision(changed)["mechanism_gate_passed"]
                )

    def test_resealed_stage_parent_effect_credit_or_privileged_tamper_fails(self) -> None:
        for kind in ("stage", "parent", "effect", "credit", "privileged"):
            changed = copy.deepcopy(self.completed[0])
            if kind == "stage":
                stage = changed["pre_effect_query_contract_receipt"]
                stage["physical_query_fetch_model_caps_unchanged"] = False
                stage.pop("receipt_payload_sha256")
                stage["receipt_payload_sha256"] = contract.payload_sha256(stage)
            elif kind == "parent":
                changed["prediction_changed"] = not changed["prediction_changed"]
            elif kind == "effect":
                changed["actual_effect_snapshot"]["model_admitted_count"] = 3
            elif kind == "credit":
                changed["positive_signed_credit_count"] = 1
            else:
                changed["category"] = "forbidden"
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = contract.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                runner.validate_task_row(changed)

    def test_forward_result_never_directly_authorizes_benchmark(self) -> None:
        aggregate = runner.aggregate_rows(self.completed, wall_seconds=1.0)
        value = contract.seal(
            {
                "artifact_version": 1,
                "role": "v25358_repaired_second_fresh_pep_forward_result",
                "protocol_id": contract.PROTOCOL_ID,
                "created_at_unix": 1,
                "execution_start_sha256": "a" * 64,
                "execution_start_payload_sha256": "b" * 64,
                "task_rows_sha256": "c" * 64,
                "prediction_freeze_sha256": "d" * 64,
                "aggregate": aggregate,
                "mechanism_decision": runner.mechanism_decision(aggregate),
                "authorization": {
                    "forward_audit": True,
                    "deepwidebench_successor_build": False,
                    "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
                    "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
                },
            },
            "result_payload_sha256",
        )
        self.assertEqual(runner.validate_forward_result(value), value)
        changed = copy.deepcopy(value)
        changed["authorization"]["deepwidebench_successor_build"] = True
        changed.pop("result_payload_sha256")
        changed = contract.seal(changed, "result_payload_sha256")
        with self.assertRaises(ValueError):
            runner.validate_forward_result(changed)

    def test_failure_row_is_terminal_content_free_and_preserves_partial_effects(self) -> None:
        budget = runner.cap.PhysicalEffectBudget()
        budget.reserve("model", 1, stage="model_plan")
        budget.reserve("query", 2, stage="shared_first_wave_search")
        row = runner._terminal_outer_failure(
            contract.task_vector()[0],
            contract.arm_order_vector()[0],
            ValueError("synthetic"),
            1.0,
            budget=budget,
            health=runner._health(),
        )
        checked = runner.validate_task_row(row)
        self.assertTrue(checked["failure_as_zero"])
        self.assertIsNone(checked["pre_effect_query_contract_receipt"])
        self.assertEqual(
            checked["actual_effect_snapshot"]["query_admitted_count"], 2
        )

    def test_forward_closure_is_label_blind_and_evaluator_absent(self) -> None:
        forbidden = {
            "category",
            "question_type",
            "task_category",
            "split",
            "ground_truth",
            "gold",
            "answer_key",
            "score",
            "reward",
        }
        accesses: list[str] = []
        for relative in contract.forward_dependency_closure(ROOT):
            if relative.suffix != ".py":
                continue
            tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Subscript)
                    and isinstance(node.slice, ast.Constant)
                    and node.slice.value in forbidden
                ):
                    accesses.append(f"{relative}:{node.slice.value}")
        self.assertEqual(accesses, [])
        self.assertFalse(
            contract.source_policy()[
                "deepwidebench_forward_evaluator_leaderboard_or_sota_authorized"
            ]
        )


if __name__ == "__main__":
    unittest.main()
