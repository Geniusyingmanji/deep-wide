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

from deepwide_agent import v24815_worldbank_successor_contract as contract  # noqa: E402
from scripts import control_v24815_worldbank_successor as control  # noqa: E402


class V24815WorldBankSuccessorTests(unittest.TestCase):
    def test_population_is_12_by_4_and_disjoint_from_prior160(self):
        private = json.loads((ROOT / contract.POPULATION_PRIVATE).read_text())
        groups = private["groups"]
        self.assertEqual(len(groups), 12)
        self.assertTrue(all(len(group) == 4 for group in groups))
        selected = {item["iso3"] for group in groups for item in group}
        self.assertEqual(len(selected), 48)
        from scripts import design_v24814_fresh_worldbank_population as population
        excluded, _ = population.base.historical_iso3(ROOT)
        self.assertTrue(selected.isdisjoint(excluded))

    def test_projected_runtime_boundary_is_exact(self):
        private = json.loads((ROOT / contract.POPULATION_PRIVATE).read_text())
        tasks = control._project_tasks(private)
        self.assertEqual(len(tasks), 12)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))
        with self.assertRaises(ValueError):
            contract.validate_task_vector([{**task, "category": "hidden"} for task in tasks])

    def test_runtime_manifest_excludes_evaluation_and_uses_new_accounting(self):
        self.assertTrue(all(path.parts[:1] != ("evaluation",) for path in contract.RUNTIME_SOURCES))
        self.assertIn(Path("src/deepwide_agent/v24812_batched_search_accounting.py"), contract.RUNTIME_SOURCES)
        child = (ROOT / contract.CHILD_MARKER).read_text()
        self.assertIn("run_v24812_task", child)
        self.assertNotIn("run_v24809_task", child)

    def test_fixed_budgets_and_high_concurrency(self):
        self.assertEqual((contract.SELECTED_COUNT, contract.EXECUTOR_CONCURRENCY, contract.MODEL_SLOT_CAP), (12, 12, 8))
        self.assertEqual(contract.LIMITS["search_queries"], 4)
        self.assertEqual(contract.LIMITS["fetch_targets"], 10)
        self.assertEqual(contract.LIMITS["model_calls"], 2)

    def test_runtime_ast_has_no_privileged_access_or_evaluator_import(self):
        fields, imports, secrets = control._ast_findings()
        self.assertEqual(fields, [])
        self.assertEqual(imports, [])
        self.assertEqual(secrets, [])


if __name__ == "__main__": unittest.main()
