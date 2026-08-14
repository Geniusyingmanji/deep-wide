from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25472_qualified_source_label_runtime as runtime  # noqa: E402
from deepwide_agent import v25476_qualified_source_label_external_contract as contract  # noqa: E402
from scripts import run_v25476_qualified_source_label_external as runner  # noqa: E402
from test_v25472_qualified_source_label_runtime import run_runtime  # noqa: E402


class _BudgetReplay:
    def __init__(self, value: dict) -> None:
        self._value = copy.deepcopy(value)

    def receipt(self) -> dict:
        return copy.deepcopy(self._value)


def completed_row() -> tuple[dict, dict, dict]:
    task = contract.task_vector()[0]
    _model, result, stage, budget = run_runtime(task=task)
    row = runner._from_runtime(
        task,
        result,
        stage,
        elapsed=1.0,
        budget=_BudgetReplay(budget),
        health=runner._health(),
    )
    return runner.validate_task_row(row), result, stage


def passing_aggregate(*, model_forwards: int = 59) -> dict:
    values = {name: 0 for name in runner.AGGREGATE_INTEGER_FIELDS}
    values.update(
        {
            "task_count": 20,
            "terminal_tasks": 20,
            "completed_runtime_tasks": 20,
            "parent_role_tasks": 20,
            "first_wave_completed_tasks": 20,
            "second_wave_completed_tasks": 20,
            "grounded_plan_provider_success_tasks": 19,
            "base_synthesis_success_tasks": 20,
            "exact_canonical_base_table_tasks": 20,
            "synthesis_capture_valid_tasks": 20,
            "captured_same_forward_page_tasks": 20,
            "captured_same_forward_page_count_total": 100,
            "accepted_unique_identity_page_tasks": 4,
            "accepted_unique_identity_page_count_total": 6,
            "available_candidate_tasks": 3,
            "available_candidate_count_total": 3,
            "applied_candidate_tasks": 3,
            "applied_coordinate_count_total": 3,
            "prediction_changed_tasks": 3,
            "all_physical_queries": 80,
            "all_physical_fetches": 200,
            "all_physical_model_forwards": model_forwards,
            "completed_physical_queries": 80,
            "completed_physical_fetches": 200,
            "completed_physical_model_forwards": model_forwards,
            "per_task_hard_cap_preserved_tasks": 20,
            "system_total_tokens": 1,
        }
    )
    return runner.validate_aggregate(
        {
            **values,
            "batch_wall_seconds": 1.0,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
            "question_prediction_query_url_page_record_value_or_credential_persisted_in_aggregate": False,
        }
    )


class V25476QualifiedSourceLabelExternalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.row, cls.result, cls.stage = completed_row()

    def test_contract_population_caps_and_quality_gate_are_frozen(self) -> None:
        self.assertEqual(len(contract.task_vector()), 20)
        self.assertEqual(contract.population.SELECTED_BLOCK_INDEX, 1)
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, 20)
        self.assertEqual(contract.MODEL_SLOT_CAP, 16)
        self.assertEqual(contract.LIMITS["search_queries"], 4)
        self.assertEqual(contract.LIMITS["model_calls"], 3)
        self.assertEqual(runner.ARMS, runtime.ARMS)
        self.assertEqual(
            contract.mechanism_gate()["maximum_normal_path_model_forwards_per_completed_task"],
            3,
        )
        self.assertTrue(
            contract.quality_gate()["candidate_whole_table_exact_strictly_greater_than_base"]
        )

    def test_real_parent_chain_decodes_and_freezes_two_predictions(self) -> None:
        decoded = runner._decode_completed(self.result, self.stage)
        self.assertEqual(set(self.row["predictions"]), set(runtime.ARMS))
        self.assertEqual(self.row["predictions"], decoded["predictions"])
        self.assertTrue(self.row["synthesis_capture_valid"])
        self.assertGreaterEqual(self.row["accepted_unique_identity_page_count"], 1)
        self.assertGreaterEqual(self.row["available_candidate_count"], 1)
        self.assertTrue(self.row["candidate_prediction_changed"])
        self.assertEqual(self.row["actual_effect_snapshot"]["query_admitted_count"], 4)
        self.assertEqual(self.row["actual_effect_snapshot"]["model_admitted_count"], 3)
        self.assertLessEqual(self.row["actual_effect_snapshot"]["fetch_admitted_count"], 14)

    def test_failure_as_zero_freezes_identical_fallback_arms(self) -> None:
        row = runner._terminal_outer_failure(
            contract.task_vector()[0], RuntimeError("synthetic"), 1.0,
            budget=None, health=None,
        )
        self.assertTrue(row["failure_as_zero"])
        self.assertEqual(len(set(row["predictions"].values())), 1)
        self.assertEqual(set(row["predictions"]), set(runtime.ARMS))

    def test_two_or_three_model_forwards_both_satisfy_upper_bound_gate(self) -> None:
        for model_forwards in (40, 59, 60):
            with self.subTest(model_forwards=model_forwards):
                decision = runner.mechanism_decision(
                    passing_aggregate(model_forwards=model_forwards)
                )
                self.assertTrue(decision["mechanism_gate_passed"])
                self.assertTrue(decision["postfreeze_quality_protocol_authorized"])

    def test_each_mechanism_threshold_fails_closed(self) -> None:
        for field, value in (
            ("synthesis_capture_valid_tasks", 19),
            ("accepted_unique_identity_page_tasks", 2),
            ("available_candidate_tasks", 1),
            ("applied_candidate_tasks", 1),
            ("prediction_changed_tasks", 1),
            ("application_failure_tasks", 1),
            ("completed_physical_model_forwards", 61),
        ):
            changed = passing_aggregate()
            changed[field] = value
            with self.subTest(field=field):
                try:
                    changed = runner.validate_aggregate(changed)
                except ValueError:
                    continue
                self.assertFalse(runner.mechanism_decision(changed)["mechanism_gate_passed"])

    def test_resealed_prediction_receipt_or_credit_tamper_fails(self) -> None:
        for kind in ("prediction", "receipt", "credit"):
            changed = copy.deepcopy(self.row)
            if kind == "prediction":
                changed["predictions"][runtime.CANDIDATE_ARM] += "x"
            elif kind == "receipt":
                changed["runtime_result"]["row_key_bound_source_receipt"][
                    "accepted_unique_identity_page_count"
                ] += 1
            else:
                changed["positive_signed_credit_count"] = 1
            changed.pop("result_payload_sha256")
            changed = contract.seal(changed, "result_payload_sha256")
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                runner.validate_task_row(changed)

    def test_forward_result_never_authorizes_quality_or_benchmark_directly(self) -> None:
        aggregate = passing_aggregate()
        value = contract.seal(
            {
                "artifact_version": 1,
                "role": runner.FORWARD_ROLE,
                "protocol_id": contract.PROTOCOL_ID,
                "aggregate": aggregate,
                "mechanism_decision": runner.mechanism_decision(aggregate),
                "authorization": {
                    "forward_audit": True,
                    "postfreeze_quality_protocol": False,
                    "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
                    "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
                },
            },
            "result_payload_sha256",
        )
        self.assertEqual(runner.validate_forward_result(value), value)

    def test_forward_closure_excludes_truth_evaluator_and_result_artifacts(self) -> None:
        paths = {str(path) for path in contract.forward_dependency_closure(ROOT)}
        self.assertFalse(any("evaluate_v254" in path for path in paths))
        self.assertFalse(any("diagnose_v254" in path for path in paths))
        self.assertFalse(any(path.startswith("results/") for path in paths))
        self.assertFalse(any(path.startswith("outputs/") for path in paths))

    def test_runtime_boundary_rejects_privileged_input_before_effect(self) -> None:
        task = {**contract.task_vector()[0], "category": "forbidden"}
        with self.assertRaises(ValueError):
            runner.run_one_task(task)


if __name__ == "__main__":
    unittest.main()
