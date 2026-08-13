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

from deepwide_agent import v25374_rfc_changed_safe_external_contract as contract  # noqa: E402
from scripts import audit_v25136_sparse_production_build as semantic  # noqa: E402
from scripts import run_v25374_rfc_changed_safe_external as runner  # noqa: E402
import test_v25370_shared_synthesis_changed_safe_runtime as fixture_module  # noqa: E402


def completed_row() -> dict:
    _inner, budget, _searches, value = (
        fixture_module.V25370SharedSynthesisChangedSafeRuntimeTests()._run()
    )
    task = contract.task_vector()[0]
    value = copy.deepcopy(value)
    value["opaque_id"] = task["opaque_id"]
    value.pop("result_payload_sha256")
    value["result_payload_sha256"] = contract.payload_sha256(value)
    return runner._from_runtime(
        task,
        value,
        budget=budget,
        health=runner._health(),
    )


def passing_aggregate() -> dict:
    return {
        "task_count": 20,
        "terminal_tasks": 20,
        "completed_runtime_tasks": 20,
        "failure_as_zero_tasks": 0,
        "first_wave_completed_tasks": 20,
        "grounded_plan_provider_success_tasks": 20,
        "base_synthesis_success_tasks": 20,
        "exact_canonical_base_table_tasks": 20,
        "verified_record_tasks": 8,
        "verified_record_count_total": 16,
        "verified_field_count_total": 24,
        "changed_safe_coordinate_tasks": 4,
        "changed_safe_coordinate_count_total": 8,
        "unchanged_verified_coordinate_count_total": 4,
        "attributable_prediction_changed_tasks": 4,
        "unattributable_prediction_changed_tasks": 0,
        "editor_validation_failure_tasks": 0,
        "outer_failure_tasks": 0,
        "budget_rejection_tasks": 0,
        "search_request_failure_count": 0,
        "unrecoverable_hard_failure_tasks": 0,
        "hard_failure_count": 0,
        "completed_physical_queries": 80,
        "completed_physical_fetches": 200,
        "completed_physical_model_forwards": 60,
        "all_physical_queries": 80,
        "all_physical_fetches": 200,
        "all_physical_model_forwards": 60,
        "per_task_hard_cap_preserved_tasks": 20,
        "positive_signed_credit_count": 0,
        "system_total_tokens": 1,
        "batch_wall_seconds": 1.0,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "contains_question_query_url_title_page_quote_record_identity_field_value_answer_or_credential": False,
    }


class V25374RfcChangedSafeExternalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.completed = completed_row()

    def test_contract_population_and_changed_safe_gate_are_frozen(self) -> None:
        self.assertEqual(len(contract.task_vector()), contract.TASK_COUNT)
        self.assertEqual(
            contract.payload_sha256(contract.task_vector()),
            contract.population.EXPECTED_TASK_VECTOR_SHA256,
        )
        self.assertEqual(contract.population.ROWS_PER_TASK, 4)
        gate = contract.mechanism_gate()
        self.assertEqual(gate["minimum_changed_safe_coordinate_tasks"], 4)
        self.assertEqual(gate["minimum_changed_safe_coordinate_count_total"], 8)
        self.assertEqual(gate["minimum_attributable_prediction_changed_tasks"], 4)
        self.assertEqual(
            gate["exact_normal_path_model_forwards_per_completed_task"], 3
        )

    def test_completed_row_binds_shared_base_editor_and_three_model_budget(self) -> None:
        row = runner.validate_task_row(self.completed)
        receipt = row["content_free_receipt"]
        self.assertTrue(row["runtime_completed"])
        self.assertEqual(row["changed_safe_coordinate_count"], 1)
        self.assertTrue(row["attributable_prediction_change"])
        self.assertEqual(row["actual_effect_snapshot"]["query_admitted_count"], 4)
        self.assertEqual(row["actual_effect_snapshot"]["model_admitted_count"], 3)
        self.assertEqual(receipt["physical_model_forward_count"], 3)
        self.assertEqual(
            receipt["changed_safe_edit_receipt"]["changed_safe_coordinate_count"],
            1,
        )
        self.assertTrue(
            receipt["one_shared_production_synthesis_is_the_control_base_table"]
        )
        self.assertTrue(receipt["candidate_has_no_independent_model_or_sampling_effect"])

    def test_gate_go_and_each_mechanism_threshold_fail_closed(self) -> None:
        aggregate = passing_aggregate()
        self.assertTrue(runner.mechanism_decision(aggregate)["mechanism_gate_passed"])
        for field, value in (
            ("verified_record_tasks", 7),
            ("verified_field_count_total", 23),
            ("changed_safe_coordinate_tasks", 3),
            ("changed_safe_coordinate_count_total", 7),
            ("attributable_prediction_changed_tasks", 3),
            ("completed_physical_model_forwards", 61),
        ):
            changed = copy.deepcopy(aggregate)
            changed[field] = value
            with self.subTest(field=field):
                self.assertFalse(
                    runner.mechanism_decision(changed)["mechanism_gate_passed"]
                )

    def test_failure_row_is_terminal_content_free_and_keeps_partial_effects(self) -> None:
        budget = runner.cap.PhysicalEffectBudget()
        budget.reserve("model", 1, stage="model_plan")
        budget.reserve("query", 2, stage="shared_first_wave_search")
        row = runner._terminal_outer_failure(
            contract.task_vector()[0],
            ValueError("synthetic"),
            1.0,
            budget=budget,
            health=runner._health(),
        )
        checked = runner.validate_task_row(row)
        self.assertTrue(checked["failure_as_zero"])
        self.assertIsNone(checked["content_free_receipt"])
        self.assertEqual(checked["changed_safe_coordinate_count"], 0)
        self.assertEqual(
            checked["actual_effect_snapshot"]["query_admitted_count"], 2
        )

    def test_resealed_editor_effect_credit_or_privileged_tamper_fails(self) -> None:
        for kind in ("editor", "effect", "credit", "privileged"):
            changed = copy.deepcopy(self.completed)
            if kind == "editor":
                changed["changed_safe_coordinate_count"] += 1
            elif kind == "effect":
                changed["actual_effect_snapshot"]["model_admitted_count"] = 4
            elif kind == "credit":
                changed["positive_signed_credit_count"] = 1
            else:
                changed["category"] = "forbidden"
            changed.pop("result_payload_sha256")
            changed = contract.seal(changed, "result_payload_sha256")
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                runner.validate_task_row(changed)

    def test_forward_result_never_directly_authorizes_benchmark(self) -> None:
        aggregate = passing_aggregate()
        value = contract.seal(
            {
                "artifact_version": 1,
                "role": "v25374_rfc_changed_safe_forward_result",
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

    def test_runtime_identity_mismatch_is_rejected(self) -> None:
        row = copy.deepcopy(self.completed)
        row["opaque_id"] = "task_deadbeefdeadbeefdeadbeef"
        row.pop("result_payload_sha256")
        row = contract.seal(row, "result_payload_sha256")
        with self.assertRaises(ValueError):
            runner.validate_task_row(row)

    def test_forward_closure_is_label_blind_and_old_populations_absent(self) -> None:
        closure = contract.forward_dependency_closure(ROOT)
        findings = semantic._semantic_findings(closure)
        self.assertEqual(findings["privileged_runtime_field_accesses"], [])
        self.assertEqual(findings["evaluator_capabilities"], [])
        self.assertEqual(findings["credential_literal_hits"], [])
        paths = {str(path) for path in closure}
        self.assertFalse(any("v25364_third_fresh_pep" in path for path in paths))
        source = (ROOT / contract.RUNNER).read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden = {
            "category", "question_type", "task_category", "split", "ground_truth",
            "gold", "answer_key", "score", "reward",
        }
        accesses = [
            node.slice.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and node.slice.value in forbidden
        ]
        self.assertEqual(accesses, [])


if __name__ == "__main__":
    unittest.main()
