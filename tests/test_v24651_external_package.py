from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24640_ror_external_evaluator import evaluate_prediction
from deepwide_agent.v24651_ror_external_contract import (
    ENTITY_GROUPS,
    task_vector,
)
from deepwide_agent.v24651_ror_external_evaluator import (
    evaluate_frozen_rows,
    gold_rows,
)


class VisibleContractTests(unittest.TestCase):
    def test_visible_boundary_and_fresh_vector(self) -> None:
        tasks = task_vector()
        self.assertEqual(len(tasks), 12)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))
        self.assertEqual(len({task["opaque_id"] for task in tasks}), 12)
        self.assertEqual(sum(len(group) for group in ENTITY_GROUPS), 48)
        self.assertEqual(len({entity for group in ENTITY_GROUPS for entity in group}), 48)

    def test_forward_contract_contains_no_private_value_or_hash(self) -> None:
        source = (
            ROOT / "src/deepwide_agent/v24651_ror_external_contract.py"
        ).read_text(encoding="utf-8")
        tree = ast.parse(source)
        self.assertNotIn("evaluation/", source)
        self.assertNotIn("external_evaluator", source)
        self.assertFalse(
            any(
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and node.value.startswith("0")
                and len(node.value) == 9
                for node in ast.walk(tree)
            )
        )

    def test_forward_sources_have_no_evaluator_or_private_population_capability(self) -> None:
        paths = (
            ROOT / "src/deepwide_agent/v24648_unknown_target_structured_runtime.py",
            ROOT / "src/deepwide_agent/v24651_ror_external_contract.py",
            ROOT / "scripts/run_v24651_ror_task.py",
            ROOT / "scripts/run_v24651_unknown_target_structured.py",
            ROOT / "scripts/audit_v24651_unknown_target_forward.py",
        )
        for path in paths:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.extend([node.module or "", *(alias.name for alias in node.names)])
            self.assertFalse(
                any("evaluator" in name.casefold() or "gold" in name.casefold() for name in imports)
            )
            self.assertNotIn("evaluation/", source)
            self.assertNotIn("v24650_ror_population_private", source)


class EvaluatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.gold = gold_rows(
            (ROOT / "evaluation/v24651_ror_gold_v1.csv").read_text(encoding="utf-8")
        )

    def test_gold_fixed_denominator_and_identity_order(self) -> None:
        self.assertEqual(len(self.gold), 48)
        self.assertEqual(len({row["opaque_id"] for row in self.gold}), 12)
        self.assertEqual(
            [row["Organization"] for row in self.gold],
            [entity for group in ENTITY_GROUPS for entity in group],
        )

    def test_full_ror_url_is_semantically_equivalent(self) -> None:
        expected = self.gold[:4]
        rows = [
            [row["Organization"], f"https://ror.org/{row['ROR ID']}", row["Country code"]]
            for row in expected
        ]
        table = (
            "| Organization | ROR ID | Country code |\n|---|---|---|\n"
            + "\n".join("| " + " | ".join(row) + " |" for row in rows)
        )
        self.assertEqual(evaluate_prediction(table, expected)["exact_table_success"], 1)

    def test_gate_requires_strict_exact_gain_and_guardrails(self) -> None:
        prediction_rows = []
        for task in task_vector():
            expected = [row for row in self.gold if row["opaque_id"] == task["opaque_id"]]
            correct = (
                "| Organization | ROR ID | Country code |\n|---|---|---|\n"
                + "\n".join(
                    f"| {row['Organization']} | {row['ROR ID']} | {row['Country code']} |"
                    for row in expected
                )
            )
            unknown = correct.replace(expected[0]["ROR ID"], "Unknown")
            prediction_rows.append(
                {
                    "opaque_id": task["opaque_id"],
                    "predictions": {
                        "baseline": unknown,
                        "unknown_target_structured": correct,
                    },
                }
            )
        metrics = evaluate_frozen_rows(prediction_rows, self.gold)
        self.assertEqual(metrics["arms"]["baseline"]["exact_table_successes"], 0)
        self.assertEqual(
            metrics["arms"]["unknown_target_structured"]["exact_table_successes"],
            12,
        )
        self.assertTrue(metrics["gate_passed"])

    def test_duplicate_task_cannot_fill_denominator(self) -> None:
        task = task_vector()[0]
        rows = [
            {
                "opaque_id": task["opaque_id"],
                "predictions": {"baseline": "x", "unknown_target_structured": "x"},
            }
            for _ in range(12)
        ]
        with self.assertRaisesRegex(ValueError, "frozen prediction drifted"):
            evaluate_frozen_rows(rows, self.gold)


if __name__ == "__main__":
    unittest.main()
