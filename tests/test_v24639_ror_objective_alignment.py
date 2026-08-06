from __future__ import annotations

import ast
import json
import sys
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path: sys.path.insert(0, str(path))

from deepwide_agent.clients import ModelResult
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits
from deepwide_agent.v24639_ror_external_contract import ENTITY_GROUPS, LIMITS, task_vector, visible_task
from deepwide_agent.v24639_ror_external_evaluator import evaluate_frozen_rows, evaluate_prediction, gold_rows
from deepwide_agent.v24639_ror_objective_runtime import extract_visible_entities, project_visible_rows, run_v24639_task, visible_query_vector


class Model:
    def __init__(self): self.requests = self.attempts = self.input_tokens = self.output_tokens = self.total_tokens = 0
    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        self.requests += 1; self.attempts += 1
        if json_mode: text = json.dumps({"language": "English", "columns": ["Organization", "ROR ID", "Country code"], "row_target_hint": "4", "queries": ["ignored"]})
        else:
            values = extract_visible_entities(visible_task(1)["question"])
            text = "```markdown\n| Organization | ROR ID | Country code |\n| --- | --- | --- |\n" + "\n".join(f"| {value} | 012345678 | ZZ |" for value in reversed(values)) + "\n```"
        return ModelResult(text, {}, None, 1)


class Search:
    def __init__(self):
        for name in ("calls", "failures", "tool_calls", "fetch_calls", "fetch_failures", "input_tokens", "output_tokens", "total_tokens"): setattr(self, name, 0)
        self.queries = []
    def search_many(self, queries, **kwargs): self.calls += 1; self.queries = list(queries); return []
    def fetch_urls(self, requests): self.fetch_calls += 1; return []


class RuntimeTests(unittest.TestCase):
    def test_visible_boundary_and_fresh_vector(self):
        tasks = task_vector(); self.assertEqual(len(tasks), 12)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))
        for index, task in enumerate(tasks): self.assertEqual(extract_visible_entities(task["question"]), list(ENTITY_GROUPS[index]))

    def test_entity_queries_and_effect_equivalence(self):
        model, search = Model(), Search()
        result = run_v24639_task(visible_task(1), model=model, search=search, limits=ScoreFirstLimits(**LIMITS), monotonic=time.monotonic)
        self.assertEqual(model.requests, 3); self.assertEqual(search.queries, visible_query_vector(visible_task(1)["question"], 4))
        self.assertFalse(result["ror_completion_receipt"]["model_search_fetch_or_token_budget_changed"])
        self.assertFalse(result["ror_completion_receipt"]["fact_value_created_by_projector"])

    def test_projection_is_ordered_and_unknown_only(self):
        entities = list(ENTITY_GROUPS[0])
        raw = "```markdown\n| Organization | ROR ID | Country code |\n| --- | --- | --- |\n| " + entities[2] + " | 012345678 | FR |\n```"
        table, receipt = project_visible_rows(raw, entities)
        self.assertEqual(receipt["matched_visible_rows"], 1); self.assertEqual(receipt["inserted_unknown_rows"], 3)
        self.assertEqual(table.count("Unknown | Unknown"), 3)

    def test_forward_has_no_gold_evaluator_import(self):
        paths = (ROOT / "src/deepwide_agent/v24639_ror_objective_runtime.py", ROOT / "src/deepwide_agent/v24639_ror_external_contract.py")
        for path in paths:
            text = path.read_text(encoding="utf-8"); tree = ast.parse(text)
            imports = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
            self.assertFalse(any("external_evaluator" in value for value in imports)); self.assertNotIn("evaluation/v24639", text)


class EvaluatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.gold = gold_rows((ROOT / "evaluation/v24639_ror_gold_v1.csv").read_text(encoding="utf-8"))
    def test_gold(self): self.assertEqual(len(self.gold), 48)
    def test_full_ror_url_is_semantically_equivalent(self):
        rows = [row for row in self.gold if row["opaque_id"] == visible_task(1)["opaque_id"]]
        table = "```markdown\n| Organization | ROR ID | Country code |\n| --- | --- | --- |\n" + "\n".join(f"| {r['Organization']} | https://ror.org/{r['ROR ID']} | {r['Country code']} |" for r in rows) + "\n```"
        self.assertEqual(evaluate_prediction(table, rows)["exact_table_success"], 1)
    def test_exact_gate(self):
        predictions = []
        for task in task_vector():
            rows = [row for row in self.gold if row["opaque_id"] == task["opaque_id"]]
            exact = "```markdown\n| Organization | ROR ID | Country code |\n| --- | --- | --- |\n" + "\n".join(f"| {r['Organization']} | {r['ROR ID']} | {r['Country code']} |" for r in rows) + "\n```"
            predictions.append({"opaque_id": task["opaque_id"], "predictions": {"baseline": "broken", "coverage_ledger": exact}})
        result = evaluate_frozen_rows(predictions, self.gold); self.assertTrue(result["gate_passed"]); self.assertEqual(result["candidate_minus_baseline"]["exact_table_successes"], 12)


if __name__ == "__main__": unittest.main()
