from __future__ import annotations

import copy
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap  # noqa: E402
from deepwide_agent import v25569_constraint_totality_safe_handoff_runtime as runtime  # noqa: E402
from deepwide_agent import v25571_fresh_totality_external_contract as contract  # noqa: E402
from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter  # noqa: E402
from scripts import run_v25571_fresh_totality_external as runner  # noqa: E402
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


class V25571FreshTotalityExternalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        first, second = contract.population.PYPI_PAIRS[0]
        cls.canonical_row = completed_row(
            0,
            table(
                [
                    [first, "2025-01-02"],
                    [second, "July 03, 2026"],
                ]
            ),
        )

    def test_contract_population_caps_and_totality_gates_are_frozen(self) -> None:
        self.assertEqual(len(contract.task_vector()), 20)
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, 20)
        self.assertEqual(contract.MODEL_SLOT_CAP, 16)
        self.assertEqual(contract.LIMITS["wall_seconds"], 240)
        self.assertEqual(contract.LIMITS["search_queries"], 4)
        self.assertEqual(contract.LIMITS["model_calls"], 3)
        gate = contract.mechanism_gate()
        self.assertEqual(gate["minimum_canonical_projection_tasks"], 1)
        self.assertEqual(gate["maximum_unsafe_handoff_tasks"], 0)

    def test_clone_namespace_and_model_pool_are_effect_ready(self) -> None:
        receipt = runner.clone_namespace_receipt()
        self.assertEqual(receipt["unresolved_function_count"], 0)
        self.assertEqual(receipt["unresolved_global_name_count"], 0)
        self.assertEqual(
            runner.model_pool_contract()["model_pool_id"],
            contract.model_pool.MODEL_POOL_ID,
        )

    def test_canonical_row_exposes_mode_and_projection_counts(self) -> None:
        row = runner.validate_task_row(self.canonical_row)
        first, second = contract.population.PYPI_PAIRS[0]
        self.assertEqual(row["projection_mode"], runtime.CANONICAL_PROJECTION)
        self.assertTrue(row["canonical_projection"])
        self.assertFalse(row["byte_exact_parent_handoff"])
        self.assertTrue(row["parent_prediction_byte_preserved"])
        self.assertEqual(row["date_cell_changed_count"], 2)
        self.assertEqual(row["sort_applied_count"], 1)
        candidate = row["predictions"][runtime.CANDIDATE_ARM]
        self.assertIn("2026年7月3日", candidate)
        self.assertLess(candidate.find(second), candidate.find(first))

    def test_noncanonical_parent_is_safe_byte_exact_handoff(self) -> None:
        task = contract.task_vector()[1]
        result, stage, budget = run_runtime(task, "not a markdown table")
        row = runner._from_runtime(
            task,
            result,
            stage,
            elapsed=1.0,
            budget=BudgetReplay(budget.receipt()),
            health=runner._health(),
        )
        self.assertEqual(
            row["projection_mode"], runtime.BYTE_EXACT_PARENT_HANDOFF
        )
        self.assertTrue(row["byte_exact_parent_handoff"])
        self.assertTrue(row["safe_handoff"])
        self.assertFalse(row["unsafe_handoff_present"])
        self.assertFalse(row["candidate_prediction_changed"])
        self.assertEqual(len(set(row["predictions"].values())), 1)
        for name in (
            "date_cell_changed_count",
            "scale_cell_changed_count",
            "sort_applied_count",
            "sort_already_satisfied_count",
            "sort_rejected_count",
        ):
            self.assertEqual(row[name], 0)

    def test_aggregate_accounts_modes_and_rejects_unsafe_handoff(self) -> None:
        rows = [self.canonical_row]
        rows.extend(
            runner._terminal_outer_failure(
                task,
                RuntimeError("synthetic-fixed-denominator"),
                1.0,
                budget=None,
                health=None,
            )
            for task in contract.task_vector()[1:]
        )
        aggregate = runner.aggregate_rows(rows, wall_seconds=1.0)
        self.assertEqual(aggregate["canonical_projection_tasks"], 1)
        self.assertEqual(aggregate["byte_exact_parent_handoff_tasks"], 0)
        self.assertEqual(aggregate["unsafe_handoff_tasks"], 0)
        self.assertFalse(runner.mechanism_decision(aggregate)["mechanism_gate_passed"])
        changed = copy.deepcopy(aggregate)
        changed["unsafe_handoff_tasks"] = 1
        with self.assertRaises(ValueError):
            runner.validate_aggregate(changed)

    def test_resealed_mode_or_handoff_modification_tamper_fails(self) -> None:
        for name, value in (
            ("projection_mode", runtime.BYTE_EXACT_PARENT_HANDOFF),
            ("byte_exact_parent_handoff", True),
            ("handoff_date_scale_sort_modification_present", True),
        ):
            changed = copy.deepcopy(self.canonical_row)
            changed[name] = value
            changed.pop("result_payload_sha256")
            changed = contract.seal(changed, "result_payload_sha256")
            with self.subTest(name=name), self.assertRaises(ValueError):
                runner.validate_task_row(changed)

    def test_internal_validation_failure_is_not_converted_to_safe_handoff(self) -> None:
        task = contract.task_vector()[0]
        result, stage, budget = run_runtime(task, "not a markdown table")
        with mock.patch.object(
            runtime, "validate_result", side_effect=ValueError("binding drift")
        ):
            with self.assertRaises(ValueError):
                runner._from_runtime(
                    task,
                    result,
                    stage,
                    elapsed=1.0,
                    budget=BudgetReplay(budget.receipt()),
                    health=runner._health(),
                )

    def test_truth_and_historical_outputs_absent_from_forward_closure(self) -> None:
        closure = {str(path) for path in contract.forward_dependency_closure(ROOT)}
        self.assertNotIn("src/deepwide_agent/v25552_pypi_stable_truth.py", closure)
        self.assertFalse(any("evaluate_v255" in path for path in closure))
        self.assertFalse(any(path.startswith("outputs/") for path in closure))


if __name__ == "__main__":
    unittest.main()
