from __future__ import annotations

import ast
import copy
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap  # noqa: E402
from deepwide_agent import v25575_canonical_column_totality_runtime as runtime  # noqa: E402
from deepwide_agent import v25579_fresh_canonical_totality_external_contract as contract  # noqa: E402
from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter  # noqa: E402
from scripts import run_v25579_fresh_canonical_totality_external as runner  # noqa: E402
from test_v25123_visible_legacy_query_compatible_runtime import limits  # noqa: E402
from test_v25349_shared_prefix_grounded_fact_paired_runtime import FactSearch  # noqa: E402


class CanonicalTotalityModel:
    def __init__(self, table: str) -> None:
        self.table = table
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self.logical_calls = 0

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        del system, user, max_output_tokens
        self.logical_calls += 1
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        if self.logical_calls == 1:
            text = json.dumps(
                {
                    "language": "English",
                    "columns": ["ignored"],
                    "queries": ["one", "two", "three", "four"],
                }
            )
        elif self.logical_calls == 2:
            text = json.dumps(
                {
                    "pivots": [],
                    "row_targets": [],
                    "authority_terms": [],
                    "queries": ["one", "two"],
                    "records": [],
                }
            )
        elif self.logical_calls == 3:
            if not json_mode:
                raise AssertionError("third call must request JSON mode")
            text = json.dumps(
                {"table": self.table, "records": []}, ensure_ascii=False
            )
        else:
            raise AssertionError("successor exceeded the three-call cap")
        return ModelResult(text=text, usage={}, response_id=None, attempts=1)


def table(index: int) -> str:
    columns = contract.population.columns_for_index(index)
    first, second = contract.population.PAIRS[index]
    return (
        "| "
        + " | ".join(columns)
        + " |\n| "
        + " | ".join("---" for _ in columns)
        + " |\n"
        + f"| {first} | 1.2.3 |\n"
        + f"| {second} | 4.5.6 |"
    )


def run_runtime(index: int):
    task = contract.task_vector()[index]
    model = CanonicalTotalityModel(table(index))
    with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
        output = Path(raw)
        slots = output / "slots"
        slots.mkdir()
        for slot in range(1, 5):
            (slots / f"slot_{slot:02d}.lock").write_text("{}\n")
        bounded = DeadlineAwareGlobalModelSlotLimiter(
            model,
            slot_directory=slots,
            output_root=output,
            slot_cap=4,
            absolute_deadline=time.monotonic() + 240,
        )
        budget = cap.PhysicalEffectBudget()
        searches = {
            phase: cap.HardCappedSearchClient(
                FactSearch(task["question"], phase), budget, phase=phase
            )
            for phase in runtime.PHASES
        }
        result, stage = runtime.run_task(
            task,
            model=cap.HardCappedModelLimiter(bounded, budget),
            searches=searches,
            limits=limits(),
            budget=budget,
            monotonic=time.monotonic,
        )
    return task, result, stage, budget, model


class BudgetReplay:
    def __init__(self, value: MappingLike) -> None:
        self.value = copy.deepcopy(dict(value))

    def receipt(self) -> dict:
        return copy.deepcopy(self.value)


MappingLike = dict


def completed_row(index: int) -> dict:
    task, result, stage, budget, _model = run_runtime(index)
    return runner._from_runtime(
        task,
        result,
        stage,
        elapsed=1.0,
        budget=BudgetReplay(budget.receipt()),
        health=runner._health(),
    )


class V25579FreshCanonicalTotalityExternalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.drift_row = completed_row(0)
        cls.ordinary_row = completed_row(contract.population.DRIFT_TASK_COUNT)

    def test_contract_population_outer_arms_caps_and_gates_are_frozen(self) -> None:
        self.assertEqual(len(contract.task_vector()), 20)
        self.assertEqual(contract.ARMS, (contract.CONTROL_ARM, contract.CANDIDATE_ARM))
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, 20)
        self.assertEqual(contract.MODEL_SLOT_CAP, 16)
        self.assertEqual(contract.LIMITS["wall_seconds"], 240)
        self.assertEqual(contract.LIMITS["search_queries"], 4)
        self.assertEqual(contract.LIMITS["model_calls"], 3)
        self.assertEqual(
            contract.payload_sha256(contract.failure_fallback_vector()),
            contract.EXPECTED_FAILURE_FALLBACK_VECTOR_SHA256,
        )
        gate = contract.mechanism_gate()
        self.assertEqual(gate["required_predecessor_counterfactual_failure_tasks"], 10)
        self.assertEqual(gate["required_successor_canonical_column_handoff_tasks"], 10)
        self.assertEqual(gate["positive_signed_credit_count"], 0)

    def test_clone_namespace_and_model_pool_are_effect_ready(self) -> None:
        receipt = runner.clone_namespace_receipt()
        self.assertEqual(receipt["unresolved_function_count"], 0)
        self.assertEqual(receipt["unresolved_global_name_count"], 0)
        self.assertEqual(
            runner.model_pool_contract()["model_pool_id"],
            contract.model_pool.MODEL_POOL_ID,
        )

    def test_drift_row_replays_exact_predecessor_failure_and_keeps_successor(self) -> None:
        row = runner.validate_task_row(self.drift_row)
        self.assertEqual(row["preassigned_exposure"], "canonical_drift")
        self.assertTrue(row["predecessor_counterfactual_evaluated"])
        self.assertTrue(row["predecessor_counterfactual_failed"])
        self.assertEqual(
            row["predecessor_counterfactual_failure_type"],
            runner.EXPECTED_PREDECESSOR_FAILURE,
        )
        self.assertEqual(row["predecessor_counterfactual_additional_effect_count"], 0)
        self.assertTrue(row["successor_canonical_column_handoff"])
        self.assertTrue(row["successor_parent_prediction_byte_preserved"])
        self.assertTrue(row["drift_fallback_to_candidate_changed"])
        self.assertNotEqual(
            row["predictions"][contract.CONTROL_ARM],
            row["predictions"][contract.CANDIDATE_ARM],
        )
        self.assertEqual(
            row["predictions"][contract.CONTROL_ARM],
            contract.failure_fallback(0),
        )
        self.assertEqual(row["actual_effect_snapshot"]["query_admitted_count"], 4)
        self.assertLessEqual(row["actual_effect_snapshot"]["fetch_admitted_count"], 14)
        self.assertEqual(row["actual_effect_snapshot"]["model_admitted_count"], 3)

    def test_ordinary_row_is_canonical_projection_and_outer_byte_identity(self) -> None:
        row = runner.validate_task_row(self.ordinary_row)
        self.assertEqual(row["preassigned_exposure"], "ordinary_ascii")
        self.assertTrue(row["predecessor_counterfactual_evaluated"])
        self.assertFalse(row["predecessor_counterfactual_failed"])
        self.assertIsNone(row["predecessor_counterfactual_failure_type"])
        self.assertTrue(row["successor_ordinary_canonical_projection"])
        self.assertFalse(row["successor_canonical_column_handoff"])
        self.assertTrue(row["ordinary_control_candidate_byte_equal"])
        self.assertEqual(len(set(row["predictions"].values())), 1)
        self.assertFalse(row["candidate_prediction_changed"])
        self.assertEqual(row["active_visible_constraint_family_count"], 0)

    def test_counterfactual_is_posteffect_local_and_budget_preserving(self) -> None:
        task, result, stage, budget, model = run_runtime(1)
        before = copy.deepcopy(budget.receipt())
        decoded = runner._decode_completed(task, result, stage)
        after = budget.receipt()
        self.assertEqual(before, after)
        self.assertEqual(model.logical_calls, 3)
        self.assertEqual(
            decoded["predecessor_counterfactual"]["additional_effect_count"], 0
        )
        self.assertTrue(
            decoded["predecessor_counterfactual"]["uses_parent_prediction_columns"]
        )
        self.assertTrue(decoded["predecessor_counterfactual"]["uses_empty_page_vector"])

    def test_aggregate_accounts_paired_estimand_and_strict_denominator(self) -> None:
        rows = []
        ordinary_index = contract.population.DRIFT_TASK_COUNT
        for index, task in enumerate(contract.task_vector()):
            if index == 0:
                rows.append(self.drift_row)
            elif index == ordinary_index:
                rows.append(self.ordinary_row)
            else:
                rows.append(
                    runner._terminal_outer_failure(
                        task,
                        RuntimeError("synthetic-fixed-denominator"),
                        1.0,
                        budget=None,
                        health=None,
                    )
                )
        aggregate = runner.aggregate_rows(rows, wall_seconds=1.0)
        self.assertEqual(aggregate["predecessor_counterfactual_failure_tasks"], 1)
        self.assertEqual(aggregate["successor_canonical_column_handoff_tasks"], 1)
        self.assertEqual(aggregate["successor_ordinary_canonical_projection_tasks"], 1)
        self.assertEqual(aggregate["ordinary_control_candidate_byte_equal_tasks"], 1)
        self.assertFalse(runner.mechanism_decision(aggregate)["mechanism_gate_passed"])

    def test_resealed_exposure_counterfactual_mode_or_prediction_tamper_fails(self) -> None:
        changes = (
            ("preassigned_exposure", "ordinary_ascii"),
            ("predecessor_counterfactual_failed", False),
            ("successor_mode", runtime.CANONICAL_PROJECTION),
            ("ordinary_control_candidate_byte_equal", True),
        )
        for name, value in changes:
            changed = copy.deepcopy(self.drift_row)
            changed[name] = value
            changed.pop("result_payload_sha256")
            changed = contract.seal(changed, "result_payload_sha256")
            with self.subTest(name=name), self.assertRaises(ValueError):
                runner.validate_task_row(changed)
        changed = copy.deepcopy(self.drift_row)
        changed["predictions"][contract.CONTROL_ARM] += "\n"
        changed["prediction_sha256"][contract.CONTROL_ARM] = __import__(
            "hashlib"
        ).sha256(changed["predictions"][contract.CONTROL_ARM].encode()).hexdigest()
        changed["candidate_prediction_changed"] = True
        changed.pop("result_payload_sha256")
        changed = contract.seal(changed, "result_payload_sha256")
        with self.assertRaises(ValueError):
            runner.validate_task_row(changed)

    def test_truth_history_and_privileged_fields_absent_from_forward_closure(self) -> None:
        closure = {str(path) for path in contract.forward_dependency_closure(ROOT)}
        self.assertNotIn("src/deepwide_agent/v25552_pypi_stable_truth.py", closure)
        self.assertFalse(any("evaluate_v255" in path for path in closure))
        self.assertFalse(any(path.startswith("outputs/") for path in closure))
        source = Path(runner.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
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
        hits = [
            str(node.slice.value)
            for node in ast.walk(tree)
            if isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and node.slice.value in forbidden
        ]
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
