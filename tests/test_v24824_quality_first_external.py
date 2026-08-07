from __future__ import annotations

import ast
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24824_quality_first_external_contract as contract  # noqa: E402
from scripts import control_v24824_quality_first_external as control  # noqa: E402
from scripts import run_v24824_quality_first_external_forward as runner  # noqa: E402


class V24824QualityFirstExternalTests(unittest.TestCase):
    def test_population_is_32_by_4_and_cell_disjoint_not_entity_disjoint(self):
        private = json.loads((ROOT / contract.POPULATION_PRIVATE).read_text())
        public = json.loads((ROOT / contract.POPULATION_DESIGN).read_text())
        groups = private["groups"]
        self.assertEqual(len(groups), 32)
        self.assertTrue(all(len(group) == 4 for group in groups))
        self.assertEqual(public["selected_gold_cell_count"], 256)
        self.assertEqual(public["selected_gold_cell_overlap_count"], 0)
        self.assertEqual(public["selected_target_pair_overlap_count"], 0)
        self.assertEqual(public["selected_entity_overlap_count"], 119)
        self.assertFalse(public["scope"]["entity_disjoint_claim"])
        self.assertTrue(public["scope"]["target_cell_disjoint_claim"])

    def test_projected_runtime_boundary_is_exact_and_value_free(self):
        private = json.loads((ROOT / contract.POPULATION_PRIVATE).read_text())
        tasks = control._project_tasks(private)
        self.assertEqual(len(tasks), 32)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))
        serialized = json.dumps(tasks)
        for group in private["groups"]:
            for item in group:
                for record in item["records"]:
                    self.assertNotIn(str(record["value"]), serialized)
        with self.assertRaises(ValueError):
            contract.validate_task_vector(
                [{**task, "question_type": "hidden"} for task in tasks]
            )

    def test_runtime_manifest_excludes_evaluation_and_uses_quality_first(self):
        self.assertTrue(
            all(path.parts[:1] != ("evaluation",) for path in contract.RUNTIME_SOURCES)
        )
        self.assertIn(
            Path("src/deepwide_agent/v24823_quality_first_accounting.py"),
            contract.RUNTIME_SOURCES,
        )
        child = (ROOT / contract.CHILD_MARKER).read_text()
        self.assertIn("run_v24823_task", child)
        self.assertNotIn("run_v24812_task", child)

    def test_fixed_budgets_high_concurrency_and_shadow_entropy(self):
        self.assertEqual(
            (
                contract.SELECTED_COUNT,
                contract.EXECUTOR_CONCURRENCY,
                contract.MODEL_SLOT_CAP,
            ),
            (32, 16, 8),
        )
        self.assertEqual(contract.LIMITS["search_queries"], 4)
        self.assertEqual(contract.LIMITS["fetch_targets"], 10)
        self.assertEqual(contract.LIMITS["model_calls"], 2)
        policy = contract.policy_dict()
        self.assertEqual(policy["information_gain_feature_weight"], 0.0)
        self.assertEqual(policy["calibration_binding"]["artifact_path"], "")

    def test_runtime_ast_has_no_privileged_access_or_evaluator_import(self):
        fields, imports, secrets = control._ast_findings()
        self.assertEqual(fields, [])
        self.assertEqual(imports, [])
        self.assertEqual(secrets, [])

    def test_progress_is_content_free_and_atomic(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "progress.json"
            for completed in (0, 1, 32):
                expected = runner.progress_value(completed)
                runner.atomic_json(path, expected)
                self.assertEqual(json.loads(path.read_text()), expected)
                encoded = path.read_text().casefold()
                for marker in (
                    '"question"',
                    '"prediction"',
                    '"opaque_id"',
                    '"credential"',
                ):
                    self.assertNotIn(marker, encoded)
            self.assertEqual(list(Path(temporary).glob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
