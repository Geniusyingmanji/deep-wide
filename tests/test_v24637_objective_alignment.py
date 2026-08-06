from __future__ import annotations

import ast
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.clients import ModelResult
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits
from deepwide_agent.v24637_external_contract import ENTITY_GROUPS, LIMITS, task_vector, visible_task
from deepwide_agent.v24637_external_evaluator import evaluate_frozen_rows, evaluate_prediction, gold_rows
from deepwide_agent.v24637_objective_alignment_runtime import (
    ARMS,
    extract_visible_entities,
    run_v24637_task,
    validate_result,
)


class FakeModel:
    def __init__(self) -> None:
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        self.requests += 1
        self.attempts += 1
        if json_mode:
            text = json.dumps(
                {
                    "language": "English",
                    "columns": ["Airport", "ICAO code", "IATA code"],
                    "row_target_hint": "8",
                    "queries": ["airport ICAO IATA codes"],
                }
            )
        else:
            entities = extract_visible_entities(visible_task(1)["question"])
            text = (
                "```markdown\n| Airport | ICAO code | IATA code |\n| --- | --- | --- |\n"
                + "\n".join(f"| {entity} | TEST | TST |" for entity in entities)
                + "\n```"
            )
        return ModelResult(text, {}, None, 1)


class FakeSearch:
    def __init__(self) -> None:
        for name in (
            "calls", "failures", "tool_calls", "fetch_calls", "fetch_failures",
            "input_tokens", "output_tokens", "total_tokens",
        ):
            setattr(self, name, 0)

    def search_many(self, queries, **kwargs):
        self.calls += 1
        return []

    def fetch_urls(self, requests):
        self.fetch_calls += 1
        return []


class ObjectiveAlignmentTests(unittest.TestCase):
    def test_visible_boundary_and_entity_round_trip(self) -> None:
        tasks = task_vector()
        self.assertEqual(len(tasks), 12)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))
        for index, task in enumerate(tasks):
            self.assertEqual(extract_visible_entities(task["question"]), list(ENTITY_GROUPS[index]))
        with self.assertRaises(ValueError):
            extract_visible_entities("hidden evaluator task")

    def test_shared_effect_budget_and_balanced_arm_order(self) -> None:
        first = run_v24637_task(
            visible_task(1), model=FakeModel(), search=FakeSearch(), limits=ScoreFirstLimits(**LIMITS)
        )
        second_model = FakeModel()
        second = run_v24637_task(
            visible_task(2), model=second_model, search=FakeSearch(), limits=ScoreFirstLimits(**LIMITS)
        )
        validate_result(first)
        validate_result(second)
        self.assertEqual(first["receipt"]["model_stage_vector"], ["shared_plan", "baseline_synthesis", "coverage_ledger_synthesis"])
        self.assertEqual(second["receipt"]["model_stage_vector"], ["shared_plan", "coverage_ledger_synthesis", "baseline_synthesis"])
        self.assertEqual(second_model.requests, 3)
        self.assertFalse(first["receipt"]["entropy_shadow"]["routes_or_changes_forward_effects"])
        self.assertFalse(first["receipt"]["entropy_shadow"]["positive_credit_assigned"])

    def test_candidate_prompt_is_exact_table_objective(self) -> None:
        model = FakeModel()
        result = run_v24637_task(
            visible_task(1), model=model, search=FakeSearch(), limits=ScoreFirstLimits(**LIMITS)
        )
        self.assertEqual(set(result["predictions"]), set(ARMS))
        self.assertTrue(result["receipt"]["candidate_changes_synthesis_objective_only"])
        self.assertFalse(result["receipt"]["candidate_additional_query_fetch_or_model_effect"])

    def test_forward_modules_have_no_evaluator_capability(self) -> None:
        paths = (
            ROOT / "src/deepwide_agent/v24637_objective_alignment_runtime.py",
            ROOT / "src/deepwide_agent/v24637_external_contract.py",
            ROOT / "scripts/run_v24637_objective_alignment_task.py",
            ROOT / "scripts/run_v24637_objective_alignment.py",
        )
        for path in paths:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.append(node.module or "")
            self.assertFalse(any("external_evaluator" in name for name in imports))
            self.assertNotIn("evaluation/v24637_ourairports_gold", path.read_text(encoding="utf-8"))
            self.assertNotIn("OURAIRPORTS_", path.read_text(encoding="utf-8"))


class ExternalEvaluatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.gold = gold_rows((ROOT / "evaluation/v24637_ourairports_gold_v1.csv").read_text(encoding="utf-8"))

    def test_gold_fixed_denominator(self) -> None:
        self.assertEqual(len(self.gold), 96)
        self.assertEqual(len({row["opaque_id"] for row in self.gold}), 12)

    def test_exact_and_failure_as_zero(self) -> None:
        rows = [row for row in self.gold if row["opaque_id"] == visible_task(1)["opaque_id"]]
        exact = (
            "```markdown\n| Airport | ICAO code | IATA code |\n| --- | --- | --- |\n"
            + "\n".join(f"| {row['Airport']} | {row['ICAO code']} | {row['IATA code']} |" for row in rows)
            + "\n```"
        )
        self.assertEqual(evaluate_prediction(exact, rows)["exact_table_success"], 1)
        self.assertEqual(evaluate_prediction("broken", rows)["composite"], 0.0)

    def test_gate_requires_exact_gain_and_composite_guardrail(self) -> None:
        predictions = []
        for task in task_vector():
            rows = [row for row in self.gold if row["opaque_id"] == task["opaque_id"]]
            exact = (
                "```markdown\n| Airport | ICAO code | IATA code |\n| --- | --- | --- |\n"
                + "\n".join(f"| {row['Airport']} | {row['ICAO code']} | {row['IATA code']} |" for row in rows)
                + "\n```"
            )
            predictions.append({"opaque_id": task["opaque_id"], "predictions": {"baseline": "broken", "coverage_ledger": exact}})
        value = evaluate_frozen_rows(predictions, self.gold)
        self.assertTrue(value["gate_passed"])
        self.assertEqual(value["candidate_minus_baseline"]["exact_table_successes"], 12)


if __name__ == "__main__":
    unittest.main()
