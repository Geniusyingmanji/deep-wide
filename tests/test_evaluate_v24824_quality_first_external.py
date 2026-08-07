from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24824_quality_first_external_contract as contract  # noqa: E402
from scripts import evaluate_v24824_quality_first_external as target  # noqa: E402
from tests.test_evaluate_v24809_worldbank_budget_ladder_smoke import (  # noqa: E402
    gold,
    question,
    table,
)


class V24824EvaluatorTests(unittest.TestCase):
    def test_exact_and_partial_metrics(self):
        exact = target.evaluate_prediction(table(complete=True), question(), gold())
        partial = target.evaluate_prediction(table(complete=False), question(), gold())
        self.assertEqual(exact["exact_table_success"], 1)
        self.assertEqual(exact["composite"], 1.0)
        self.assertEqual(partial["exact_table_success"], 0)
        self.assertLess(partial["item_f1"], exact["item_f1"])

    def test_private_population_is_complete_and_32_tasks(self):
        private = target.read(ROOT / target.PRIVATE)
        gold_rows = target._private_gold(private)
        self.assertEqual(len(gold_rows), contract.SELECTED_COUNT)
        self.assertTrue(all(len(rows) == 4 for rows in gold_rows.values()))

    def test_evaluator_excluded_from_runtime_manifest(self):
        self.assertNotIn(
            Path("scripts/evaluate_v24824_quality_first_external.py"),
            contract.RUNTIME_SOURCES,
        )
        self.assertTrue(
            all(path.parts[:1] != ("evaluation",) for path in contract.RUNTIME_SOURCES)
        )

    def test_frozen_predictions_are_adaptive_fixed_identical(self):
        protocol, _audit = target.validate_parent()
        predictions = [
            target.json.loads(line)
            for line in (ROOT / contract.PREDICTIONS)
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        gold_rows = target._private_gold(target.read(ROOT / target.PRIVATE))
        metrics = target.evaluate_rows(predictions, protocol, gold_rows)
        self.assertEqual(
            metrics["adaptive_prediction_equals_fixed_full_tasks"], 32
        )
        self.assertEqual(
            set(metrics["adaptive_minus_fixed_full"].values()), {0}
        )


if __name__ == "__main__":
    unittest.main()
