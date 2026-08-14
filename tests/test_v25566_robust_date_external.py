from __future__ import annotations

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
from deepwide_agent import v25545_deterministic_visible_constraint_runtime as runtime  # noqa: E402
from deepwide_agent import v25566_robust_date_external_contract as contract  # noqa: E402
from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter  # noqa: E402
from scripts import run_v25566_robust_date_external as runner  # noqa: E402
from test_v25123_visible_legacy_query_compatible_runtime import limits  # noqa: E402
from test_v25349_shared_prefix_grounded_fact_paired_runtime import FactSearch  # noqa: E402


class ConstraintModel:
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
        else:
            if not json_mode:
                raise AssertionError("third call must request JSON mode")
            text = json.dumps({"table": self.table, "records": []})
        return ModelResult(text=text, usage={}, response_id=None, attempts=1)


def table(rows: list[list[str]]) -> str:
    columns = contract.population.DATE_COLUMNS
    return (
        "| "
        + " | ".join(columns)
        + " |\n| "
        + " | ".join("---" for _ in columns)
        + " |\n"
        + "\n".join("| " + " | ".join(row) + " |" for row in rows)
    )


def run_runtime(task: dict[str, str], prediction: str):
    model = ConstraintModel(prediction)
    with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
        output = Path(raw)
        slots = output / "slots"
        slots.mkdir()
        for index in range(1, 5):
            (slots / f"slot_{index:02d}.lock").write_text("{}\n")
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
    return result, stage, budget


class BudgetReplay:
    def __init__(self, value: dict) -> None:
        self.value = copy.deepcopy(value)

    def receipt(self) -> dict:
        return copy.deepcopy(self.value)


def completed_row(index: int, prediction: str) -> dict:
    task = contract.task_vector()[index]
    result, stage, budget = run_runtime(task, prediction)
    return runner._from_runtime(
        task,
        result,
        stage,
        elapsed=1.0,
        budget=BudgetReplay(budget.receipt()),
        health=runner._health(),
    )


class V25566FreshDateExternalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        first, second = contract.population.PYPI_PAIRS[0]
        cls.row = completed_row(
            0,
            table(
                [
                    [first, "2025-01-02"],
                    [second, "July 03, 2026"],
                ]
            ),
        )

    def test_contract_population_caps_and_date_only_gates_are_frozen(self) -> None:
        self.assertEqual(len(contract.task_vector()), 20)
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, 20)
        self.assertEqual(contract.MODEL_SLOT_CAP, 16)
        self.assertEqual(contract.LIMITS["search_queries"], 4)
        self.assertEqual(contract.LIMITS["model_calls"], 3)
        self.assertEqual(contract.population.DATE_TASK_COUNT, 20)
        self.assertEqual(contract.population.SCALE_TASK_COUNT, 0)
        gate = contract.mechanism_gate()
        self.assertEqual(gate["minimum_date_contract_tasks"], 20)
        self.assertEqual(gate["minimum_scale_contract_tasks"], 0)
        self.assertEqual(gate["minimum_candidate_prediction_changed_tasks"], 2)

    def test_clone_namespace_resolves_effect_infrastructure_before_effect(self) -> None:
        receipt = runner.clone_namespace_receipt()
        self.assertEqual(receipt["unresolved_function_count"], 0)
        self.assertEqual(receipt["unresolved_global_name_count"], 0)
        for name in (
            "fcntl_resolved",
            "socket_resolved",
            "subprocess_resolved",
            "thread_pool_executor_resolved",
            "as_completed_resolved",
            "lease_helper_resolved",
        ):
            self.assertTrue(receipt[name])

    def test_date_chain_reformats_and_stably_sorts_shared_parent(self) -> None:
        row = runner.validate_task_row(self.row)
        first, second = contract.population.PYPI_PAIRS[0]
        self.assertTrue(row["runtime_completed"])
        self.assertTrue(row["date_contract_active"])
        self.assertFalse(row["scale_contract_active"])
        self.assertTrue(row["order_contract_active"])
        self.assertEqual(row["date_cell_changed_count"], 2)
        self.assertEqual(row["scale_cell_changed_count"], 0)
        self.assertEqual(row["sort_applied_count"], 1)
        candidate = row["predictions"][runtime.CANDIDATE_ARM]
        self.assertIn("2026年7月3日", candidate)
        self.assertLess(candidate.find(second), candidate.find(first))

    def test_unknown_remains_byte_exact_and_sort_fails_closed(self) -> None:
        first, second = contract.population.PYPI_PAIRS[1]
        row = completed_row(
            1,
            table([[first, "Unknown"], [second, "2026-02-03"]]),
        )
        self.assertEqual(row["date_cell_changed_count"], 1)
        self.assertEqual(row["sort_applied_count"], 0)
        self.assertEqual(row["sort_rejected_count"], 1)
        candidate = row["predictions"][runtime.CANDIDATE_ARM]
        self.assertIn("Unknown", candidate)
        self.assertLess(candidate.find(first), candidate.find(second))

    def test_twenty_row_aggregate_has_fixed_denominator_and_scale_zero(self) -> None:
        rows = [self.row]
        for task in contract.task_vector()[1:]:
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
        decision = runner.mechanism_decision(aggregate)
        self.assertEqual(aggregate["task_count"], 20)
        self.assertEqual(aggregate["completed_runtime_tasks"], 1)
        self.assertEqual(aggregate["failure_as_zero_tasks"], 19)
        self.assertEqual(aggregate["scale_contract_tasks"], 0)
        self.assertEqual(aggregate["scale_changed_tasks"], 0)
        self.assertFalse(decision["mechanism_gate_passed"])

    def test_failure_as_zero_freezes_identical_fallback_arms(self) -> None:
        row = runner._terminal_outer_failure(
            contract.task_vector()[0],
            RuntimeError("synthetic"),
            1.0,
            budget=None,
            health=None,
        )
        self.assertTrue(row["failure_as_zero"])
        self.assertEqual(len(set(row["predictions"].values())), 1)
        self.assertFalse(row["candidate_prediction_changed"])
        self.assertFalse(row["scale_contract_active"])

    def test_truth_totality_is_absent_from_forward_dependency_closure(self) -> None:
        closure = {str(path) for path in contract.forward_dependency_closure(ROOT)}
        self.assertNotIn("src/deepwide_agent/v25552_pypi_stable_truth.py", closure)
        self.assertFalse(any("evaluate_v255" in path for path in closure))

    def test_task_row_resealed_role_population_or_scale_tamper_fails(self) -> None:
        for kind in ("role", "opaque", "scale"):
            changed = copy.deepcopy(self.row)
            if kind == "role":
                changed["role"] = "v25550_visible_constraint_frozen_task_result"
            elif kind == "opaque":
                changed["opaque_id"] = "task_" + "0" * 24
            else:
                changed["scale_contract_active"] = True
            changed.pop("result_payload_sha256")
            changed = contract.seal(changed, "result_payload_sha256")
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                runner.validate_task_row(changed)


if __name__ == "__main__":
    unittest.main()
