from __future__ import annotations

import ast
import csv
import io
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24639_ror_objective_runtime import extract_visible_entities
from deepwide_agent.v24645_ror_external_contract import (
    ENTITY_GROUPS,
    SELECTED_COUNT,
    task_vector,
    visible_task,
)
from deepwide_agent.v24645_ror_external_evaluator import (
    evaluate_frozen_rows,
    evaluate_prediction,
    gold_rows,
)


def table(rows: list[list[str]]) -> str:
    return (
        "```markdown\n| Organization | ROR ID | Country code |\n"
        "| --- | --- | --- |\n"
        + "\n".join("| " + " | ".join(row) + " |" for row in rows)
        + "\n```"
    )


class VisibleContractTests(unittest.TestCase):
    def test_visible_boundary_and_fresh_vector(self) -> None:
        tasks = task_vector()
        self.assertEqual(len(tasks), SELECTED_COUNT)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))
        self.assertEqual(len({task["opaque_id"] for task in tasks}), SELECTED_COUNT)
        for index, task in enumerate(tasks):
            self.assertEqual(
                extract_visible_entities(task["question"]), list(ENTITY_GROUPS[index])
            )

    def test_forward_sources_have_no_evaluator_or_private_population_capability(self) -> None:
        paths = (
            ROOT / "src/deepwide_agent/v24644_primary_identity_pair_runtime.py",
            ROOT / "src/deepwide_agent/v24645_ror_external_contract.py",
            ROOT / "scripts/run_v24645_ror_task.py",
        )
        forbidden_literals = (
            "evaluation/v24645",
            "v24645_ror_population_private",
            "v24645_ror_gold",
            "GOLD",
            "PROVENANCE",
        )
        for path in paths:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            imports: list[str] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.append(node.module or "")
            self.assertFalse(
                any("evaluator" in name.casefold() or "gold" in name.casefold() for name in imports)
            )
            for literal in forbidden_literals:
                self.assertNotIn(literal, source)
        child = paths[-1].read_text(encoding="utf-8")
        self.assertIn("run_v24644_task", child)
        self.assertNotIn("run_v24642_task", child)

    def test_forward_contract_contains_no_private_value_or_hash(self) -> None:
        private = json.loads(
            (ROOT / "evaluation/v24645_ror_population_private_v1_20260806.json").read_text(
                encoding="utf-8"
            )
        )
        source = (
            ROOT / "src/deepwide_agent/v24645_ror_external_contract.py"
        ).read_text(encoding="utf-8")
        for record in private["records"]:
            self.assertNotIn(record["record_id"], source)
            self.assertNotIn(record["git_blob_sha1"], source)
            self.assertNotIn(record["record_bytes_sha256"], source)


class EvaluatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.gold = gold_rows(
            (ROOT / "evaluation/v24645_ror_gold_v1.csv").read_text(encoding="utf-8")
        )

    def test_gold_fixed_denominator_and_identity_order(self) -> None:
        self.assertEqual(len(self.gold), 48)
        self.assertEqual(len({row["opaque_id"] for row in self.gold}), 12)
        self.assertEqual(
            [row["Organization"] for row in self.gold],
            [entity for group in ENTITY_GROUPS for entity in group],
        )

    def test_full_ror_url_is_semantically_equivalent(self) -> None:
        rows = [
            row for row in self.gold if row["opaque_id"] == visible_task(1)["opaque_id"]
        ]
        exact = table(
            [
                [
                    row["Organization"],
                    "https://ror.org/" + row["ROR ID"],
                    row["Country code"],
                ]
                for row in rows
            ]
        )
        self.assertEqual(evaluate_prediction(exact, rows)["exact_table_success"], 1)

    def test_gate_requires_strict_exact_gain_and_guardrails(self) -> None:
        predictions = []
        for task in task_vector():
            rows = [row for row in self.gold if row["opaque_id"] == task["opaque_id"]]
            exact = table(
                [
                    [row["Organization"], row["ROR ID"], row["Country code"]]
                    for row in rows
                ]
            )
            predictions.append(
                {
                    "opaque_id": task["opaque_id"],
                    "predictions": {"baseline": "broken", "deterministic_pair": exact},
                }
            )
        value = evaluate_frozen_rows(predictions, self.gold)
        self.assertTrue(value["gate_passed"])
        self.assertEqual(
            value["candidate_minus_baseline"]["exact_table_successes"], 12
        )
        tied = [
            {
                "opaque_id": row["opaque_id"],
                "predictions": {
                    "baseline": row["predictions"]["deterministic_pair"],
                    "deterministic_pair": row["predictions"]["deterministic_pair"],
                },
            }
            for row in predictions
        ]
        self.assertFalse(evaluate_frozen_rows(tied, self.gold)["gate_passed"])

    def test_duplicate_task_cannot_fill_denominator(self) -> None:
        rows = [row for row in self.gold if row["opaque_id"] == visible_task(1)["opaque_id"]]
        exact = table(
            [[row["Organization"], row["ROR ID"], row["Country code"]] for row in rows]
        )
        duplicated = [
            {
                "opaque_id": visible_task(1)["opaque_id"],
                "predictions": {"baseline": exact, "deterministic_pair": exact},
            }
            for _ in range(SELECTED_COUNT)
        ]
        with self.assertRaisesRegex(ValueError, "frozen prediction drifted"):
            evaluate_frozen_rows(duplicated, self.gold)


if __name__ == "__main__":
    unittest.main()
