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

from deepwide_agent import v25353_fresh_pep_grounded_fact_external_contract as contract  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from scripts import run_v25353_fresh_pep_grounded_fact_external as runner  # noqa: E402
import test_v25349_shared_prefix_grounded_fact_paired_runtime as fixture_module  # noqa: E402


def completed_row(index: int, *, exposed: bool) -> dict:
    fixture = fixture_module.V25349SharedPrefixGroundedFactPairedRuntimeTests()
    _inner, budget, _searches, result = fixture._run(
        joint=exposed,
        arm_order=contract.arm_order_vector()[index],
    )
    changed = copy.deepcopy(result)
    task = contract.task_vector()[index]
    changed["opaque_id"] = task["opaque_id"]
    changed.pop("result_payload_sha256")
    changed["result_payload_sha256"] = payload_sha256(changed)
    return runner._from_runtime(
        task,
        contract.arm_order_vector()[index],
        changed,
        budget=budget,
        health=runner._health(),
    )


class V25353FreshPepGroundedFactExternalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = [
            completed_row(index, exposed=index < 12)
            for index in range(contract.TASK_COUNT)
        ]

    def test_population_protocol_surface_is_visible_balanced_and_credit_zero(self) -> None:
        tasks = contract.task_vector()
        orders = contract.arm_order_vector()
        self.assertEqual(len(tasks), 20)
        self.assertEqual(len({task["opaque_id"] for task in tasks}), 20)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))
        self.assertEqual(sum(order[0] == contract.CANDIDATE_ARM for order in orders), 10)
        policy = contract.source_policy()
        self.assertTrue(policy["proposal_identity_directly_visible_in_question"])
        self.assertTrue(policy["hidden_clue_identity_mapping_absent"])
        self.assertFalse(policy["entropy_or_information_gain_assigns_signed_credit"])

    def test_completed_task_rows_validate_and_bind_physical_effects(self) -> None:
        row = runner.validate_task_row(self.rows[0])
        receipt = row["content_free_receipt"]
        effects = row["actual_effect_snapshot"]
        self.assertEqual(effects["query_admitted_count"], 4)
        self.assertLessEqual(effects["fetch_admitted_count"], 14)
        self.assertEqual(effects["model_admitted_count"], 4)
        self.assertEqual(effects["query_admitted_count"], receipt["physical_query_count"])
        self.assertEqual(effects["fetch_admitted_count"], receipt["physical_fetch_count"])
        self.assertEqual(effects["model_admitted_count"], receipt["physical_model_forward_count"])
        self.assertTrue(row["candidate_production_prompt_changed"])
        self.assertTrue(row["attributable_prediction_change"])

    def test_mechanism_gate_go_requires_fact_exposure_and_attribution(self) -> None:
        aggregate = runner.aggregate_rows(self.rows, wall_seconds=1.0)
        decision = runner.mechanism_decision(aggregate)
        self.assertTrue(decision["mechanism_gate_passed"])
        self.assertTrue(decision["deepwidebench_successor_build_authorized"])
        for field in (
            "candidate_prompt_changed_tasks",
            "verified_record_tasks",
            "verified_field_count_total",
            "attributable_prediction_changed_tasks",
        ):
            changed = copy.deepcopy(aggregate)
            changed[field] = 0
            with self.subTest(field=field):
                self.assertFalse(
                    runner.mechanism_decision(changed)["mechanism_gate_passed"]
                )

    def test_gate_rejects_unattributable_failure_budget_or_credit_drift(self) -> None:
        aggregate = runner.aggregate_rows(self.rows, wall_seconds=1.0)
        mutations = {
            "unattributable_prediction_changed_tasks": 1,
            "outer_failure_tasks": 1,
            "budget_rejection_tasks": 1,
            "hard_failure_count": 1,
            "physical_queries": aggregate["physical_queries"] - 1,
            "physical_model_forwards": aggregate["physical_model_forwards"] - 1,
            "positive_signed_credit_count": 1,
        }
        for field, value in mutations.items():
            changed = copy.deepcopy(aggregate)
            changed[field] = value
            with self.subTest(field=field):
                self.assertFalse(
                    runner.mechanism_decision(changed)["mechanism_gate_passed"]
                )

    def test_failure_as_zero_is_terminal_and_preserves_effect_snapshot(self) -> None:
        from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap

        budget = cap.PhysicalEffectBudget()
        budget.reserve("model", 1, stage="model_plan")
        failure = runner._terminal_outer_failure(
            contract.task_vector()[0],
            contract.arm_order_vector()[0],
            RuntimeError("synthetic"),
            1.0,
            budget=budget,
            health=runner._health(),
        )
        checked = runner.validate_task_row(failure)
        self.assertTrue(checked["terminal"])
        self.assertTrue(checked["failure_as_zero"])
        self.assertEqual(
            checked["actual_effect_snapshot"]["model_admitted_count"], 1
        )
        rows = [failure, *self.rows[1:]]
        self.assertFalse(
            runner.mechanism_decision(
                runner.aggregate_rows(rows, wall_seconds=1.0)
            )["mechanism_gate_passed"]
        )

    def test_resealed_privileged_credit_effect_or_attribution_tamper_fails(self) -> None:
        for kind in ("privileged", "credit", "effect", "attribution"):
            changed = copy.deepcopy(self.rows[0])
            if kind == "privileged":
                changed["category"] = "forbidden"
            elif kind == "credit":
                changed["positive_signed_credit_count"] = 1
            elif kind == "effect":
                changed["actual_effect_snapshot"]["model_admitted_count"] = 3
            else:
                changed["attributable_prediction_change"] = False
            changed.pop("result_payload_sha256")
            changed = contract.seal(changed, "result_payload_sha256")
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                runner.validate_task_row(changed)

    def test_forward_result_never_directly_authorizes_benchmark(self) -> None:
        aggregate = runner.aggregate_rows(self.rows, wall_seconds=1.0)
        decision = runner.mechanism_decision(aggregate)
        value = contract.seal(
            {
                "artifact_version": 1,
                "role": "v25353_fresh_pep_grounded_fact_external_forward_result",
                "protocol_id": contract.PROTOCOL_ID,
                "created_at_unix": 1,
                "execution_start_sha256": "a" * 64,
                "execution_start_payload_sha256": "b" * 64,
                "task_rows_sha256": "c" * 64,
                "prediction_freeze_sha256": "d" * 64,
                "aggregate": aggregate,
                "mechanism_decision": decision,
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
        for relative in (contract.RUNNER, contract.RUNTIME, contract.POPULATION):
            tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Subscript) and isinstance(
                    node.slice, ast.Constant
                ):
                    if node.slice.value in forbidden:
                        accesses.append(str(node.slice.value))
        self.assertEqual(accesses, [])
        self.assertFalse(
            contract.source_policy()[
                "deepwidebench_forward_evaluator_leaderboard_or_sota_authorized"
            ]
        )


if __name__ == "__main__":
    unittest.main()
