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
from deepwide_agent import v25550_visible_constraint_external_contract as contract  # noqa: E402
from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter  # noqa: E402
from scripts import run_v25550_visible_constraint_external as runner  # noqa: E402
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


def _table(columns: tuple[str, ...], rows: list[list[str]]) -> str:
    return (
        "| "
        + " | ".join(columns)
        + " |\n| "
        + " | ".join("---" for _ in columns)
        + " |\n"
        + "\n".join("| " + " | ".join(row) + " |" for row in rows)
    )


def run_runtime(task: dict[str, str], table: str):
    model = ConstraintModel(table)
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
    return model, result, stage, budget


class _BudgetReplay:
    def __init__(self, value: dict) -> None:
        self._value = copy.deepcopy(value)

    def receipt(self) -> dict:
        return copy.deepcopy(self._value)


def completed_row(index: int, table: str) -> tuple[dict, dict, dict]:
    task = contract.task_vector()[index]
    _model, result, stage, budget = run_runtime(task, table)
    row = runner._from_runtime(
        task,
        result,
        stage,
        elapsed=1.0,
        budget=_BudgetReplay(budget.receipt()),
        health=runner._health(),
    )
    return runner.validate_task_row(row), result, stage


class V25550VisibleConstraintExternalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.date_row, cls.date_result, cls.date_stage = completed_row(
            0,
            _table(
                contract.population.DATE_COLUMNS,
                [["marimo", "2025-01-02"], ["solara", "July 03, 2026"]],
            ),
        )
        cls.scale_row, cls.scale_result, cls.scale_stage = completed_row(
            contract.population.DATE_TASK_COUNT,
            _table(
                contract.population.SCALE_COLUMNS,
                [
                    ["HuggingFaceTB/SmolLM2-135M-Instruct", "360 million"],
                    ["HuggingFaceTB/SmolLM2-360M-Instruct", "1.7 billion"],
                ],
            ),
        )

    def test_contract_population_caps_and_gates_are_frozen(self) -> None:
        self.assertEqual(len(contract.task_vector()), 20)
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, 20)
        self.assertEqual(contract.MODEL_SLOT_CAP, 16)
        self.assertEqual(contract.LIMITS["search_queries"], 4)
        self.assertEqual(contract.LIMITS["model_calls"], 3)
        self.assertEqual(runner.ARMS, runtime.ARMS)
        self.assertEqual(
            contract.mechanism_gate()["minimum_candidate_prediction_changed_tasks"],
            2,
        )
        self.assertTrue(
            contract.quality_gate()["candidate_exact_strictly_greater_than_control"]
        )

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
        row = self.date_row
        self.assertTrue(row["runtime_completed"])
        self.assertTrue(row["date_contract_active"])
        self.assertTrue(row["order_contract_active"])
        self.assertEqual(row["date_cell_changed_count"], 2)
        self.assertEqual(row["sort_applied_count"], 1)
        self.assertTrue(row["candidate_prediction_changed"])
        control = row["predictions"][runtime.CONTROL_ARM]
        candidate = row["predictions"][runtime.CANDIDATE_ARM]
        self.assertIn("2026年7月3日", candidate)
        self.assertLess(candidate.find("solara"), candidate.find("marimo"))
        self.assertNotEqual(control, candidate)

    def test_scale_chain_converts_but_rejects_coupled_lexical_sort(self) -> None:
        row = self.scale_row
        self.assertTrue(row["scale_contract_active"])
        self.assertTrue(row["order_contract_active"])
        self.assertEqual(row["scale_cell_changed_count"], 1)
        self.assertEqual(row["sort_applied_count"], 0)
        self.assertEqual(row["sort_rejected_count"], 1)
        candidate = row["predictions"][runtime.CANDIDATE_ARM]
        self.assertIn("1700 million", candidate)
        self.assertLess(candidate.find("135M-Instruct"), candidate.find("360M-Instruct"))

    def test_twenty_row_aggregate_recomputes_fixed_denominator(self) -> None:
        rows = []
        for index, task in enumerate(contract.task_vector()):
            if index == 0:
                rows.append(self.date_row)
            elif index == contract.population.DATE_TASK_COUNT:
                rows.append(self.scale_row)
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
        decision = runner.mechanism_decision(aggregate)
        self.assertEqual(aggregate["task_count"], 20)
        self.assertEqual(aggregate["completed_runtime_tasks"], 2)
        self.assertEqual(aggregate["failure_as_zero_tasks"], 18)
        self.assertEqual(aggregate["date_changed_tasks"], 1)
        self.assertEqual(aggregate["scale_changed_tasks"], 1)
        self.assertEqual(aggregate["sort_applied_tasks"], 1)
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
        self.assertEqual(row["active_family_count"], 0)

    def test_resealed_prediction_receipt_credit_or_attribution_tamper_fails(self) -> None:
        for kind in ("prediction", "receipt", "credit", "attribution"):
            changed = copy.deepcopy(self.date_row)
            if kind == "prediction":
                changed["predictions"][runtime.CANDIDATE_ARM] += "x"
            elif kind == "receipt":
                changed["runtime_result"]["deterministic_visible_constraint_receipt"][
                    "sort_applied_count"
                ] = 0
            elif kind == "credit":
                changed["positive_signed_credit_count"] = 1
            else:
                changed["unattributable_prediction_change_present"] = True
            changed.pop("result_payload_sha256")
            changed = contract.seal(changed, "result_payload_sha256")
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                runner.validate_task_row(changed)

    def test_forward_closure_excludes_truth_evaluator_and_result_artifacts(self) -> None:
        paths = {str(path) for path in contract.forward_dependency_closure(ROOT)}
        self.assertIn(str(contract.CLONE_HELPER), paths)
        self.assertFalse(any("evaluate_v25550" in path for path in paths))
        self.assertFalse(any(path.startswith("results/") for path in paths))
        self.assertFalse(any(path.startswith("outputs/") for path in paths))

    def test_runtime_boundary_rejects_privileged_input_before_effect(self) -> None:
        task = {**contract.task_vector()[0], "category": "forbidden"}
        with self.assertRaises(ValueError):
            runner.run_one_task(task)


if __name__ == "__main__":
    unittest.main()
