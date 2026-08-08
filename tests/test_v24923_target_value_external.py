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

from deepwide_agent import v24923_target_value_external_contract as contract  # noqa: E402
from scripts import evaluate_v24923_target_value_external as evaluator  # noqa: E402
from scripts import run_v24923_target_value_external as runner  # noqa: E402
from scripts import run_v24923_target_value_external_task as child  # noqa: E402


def synthetic_snapshot() -> tuple[bytes, list[bytes]]:
    def iso3(index: int) -> str:
        return "".join(
            (
                chr(65 + (index // (26 * 26)) % 26),
                chr(65 + (index // 26) % 26),
                chr(65 + index % 26),
            )
        )

    catalog = [
        {
            "id": iso3(index),
            "name": f"Country {index:03d}",
            "region": {"id": "TST"},
        }
        for index in range(190)
    ]
    target_blobs = []
    for target_index in range(len(contract.TARGETS)):
        rows = [
            {
                "country": {"value": item["name"]},
                "countryiso3code": item["id"],
                "value": f"{target_index + 1}.{index:03d}",
            }
            for index, item in enumerate(catalog)
        ]
        target_blobs.append(json.dumps([{}, rows]).encode())
    return json.dumps([{}, catalog]).encode(), target_blobs


class V24923TargetValueExternalTests(unittest.TestCase):
    def test_confirmatory_targets_are_fixed_and_development_disjoint(self) -> None:
        self.assertEqual(len(contract.TARGETS), 4)
        self.assertTrue(
            set(contract.TARGET_KEYS).isdisjoint(contract.DEVELOPMENT_TARGET_KEYS)
        )

    def test_task_vector_is_12x12_and_label_blind(self) -> None:
        catalog_blob, target_blobs = synthetic_snapshot()
        bundle, tasks, freeze = runner.build_snapshot(catalog_blob, target_blobs)
        self.assertEqual(len(tasks), 12)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))
        self.assertTrue(
            all(len(contract.parse_visible_countries(task["question"])) == 12 for task in tasks)
        )
        self.assertEqual(len(bundle["pages"]), 4)
        self.assertEqual(freeze["selected_entities"], 144)

    def test_task_vector_rejects_privileged_field(self) -> None:
        catalog_blob, target_blobs = synthetic_snapshot()
        _bundle, tasks, _freeze = runner.build_snapshot(catalog_blob, target_blobs)
        with self.assertRaises(ValueError):
            contract.validate_task_vector(
                [{**task, "question_type": "hidden"} for task in tasks]
            )

    def test_task_vector_rejects_cross_task_entity_reuse(self) -> None:
        catalog_blob, target_blobs = synthetic_snapshot()
        _bundle, tasks, _freeze = runner.build_snapshot(catalog_blob, target_blobs)
        altered = [dict(task) for task in tasks]
        first = contract.parse_visible_countries(altered[0]["question"])[0]
        second = contract.parse_visible_countries(altered[1]["question"])[0]
        altered[1]["question"] = altered[1]["question"].replace(
            f"1. {second[0]} [{second[1]}]", f"1. {first[0]} [{first[1]}]"
        )
        with self.assertRaises(ValueError):
            contract.validate_task_vector(altered)

    def test_both_arms_use_same_30k_and_5k_caps(self) -> None:
        catalog_blob, target_blobs = synthetic_snapshot()
        bundle, tasks, _freeze = runner.build_snapshot(catalog_blob, target_blobs)
        values = child.build_projections(tasks[0]["question"], bundle["pages"])
        for arm in contract.ARMS:
            policy = values[arm]["receipt"]["policy"]
            self.assertEqual(policy["total_character_cap"], 30_000)
            self.assertEqual(policy["maximum_page_chars"], 5_000)

    def test_target_value_receipt_is_engaged_on_synthetic_tables(self) -> None:
        catalog_blob, target_blobs = synthetic_snapshot()
        bundle, tasks, _freeze = runner.build_snapshot(catalog_blob, target_blobs)
        values = child.build_projections(tasks[0]["question"], bundle["pages"])
        receipt = values["target_value_30k"]["receipt"]
        self.assertGreater(receipt["supported_target_value_pair_count"], 0)
        self.assertGreater(receipt["retained_target_value_pair_count"], 0)
        self.assertFalse(receipt["entropy_or_information_gain_assigns_credit"])

    def test_prompt_has_no_evaluator_or_ground_truth(self) -> None:
        prompt = child._prompt("VISIBLE QUESTION", "VISIBLE EVIDENCE")
        self.assertIn("VISIBLE QUESTION", prompt)
        self.assertIn("VISIBLE EVIDENCE", prompt)
        self.assertNotIn("ground_truth", prompt)
        self.assertNotIn("evaluator", prompt)

    def test_evaluator_exact_table(self) -> None:
        catalog_blob, target_blobs = synthetic_snapshot()
        bundle, tasks, _freeze = runner.build_snapshot(catalog_blob, target_blobs)
        gold = evaluator.build_gold(tasks, bundle)
        opaque = tasks[0]["opaque_id"]
        columns = contract.visible_columns()
        lines = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
        for row in gold[opaque]:
            lines.append("| " + " | ".join(row[column] for column in columns) + " |")
        metric = evaluator.evaluate_prediction("\n".join(lines), gold[opaque])
        self.assertEqual(metric["exact_table_success"], 1)
        self.assertEqual(metric["composite"], 1.0)

    def test_go_delta_is_candidate_minus_parent(self) -> None:
        catalog_blob, target_blobs = synthetic_snapshot()
        bundle, tasks, _freeze = runner.build_snapshot(catalog_blob, target_blobs)
        gold = evaluator.build_gold(tasks, bundle)
        rows = []
        columns = contract.visible_columns()
        for task in tasks:
            lines = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
            for row in gold[task["opaque_id"]]:
                lines.append("| " + " | ".join(row[column] for column in columns) + " |")
            exact = "\n".join(lines)
            rows.append(
                {
                    "opaque_id": task["opaque_id"],
                    "predictions": {
                        "parent_30k": exact,
                        "target_value_30k": exact,
                    },
                }
            )
        metrics = evaluator.evaluate_rows(rows, gold)
        self.assertEqual(
            metrics["target_value_30k_minus_parent_30k"][
                "exact_table_successes"
            ],
            0,
        )

    def test_forward_runtime_does_not_import_evaluator(self) -> None:
        for relative in (contract.RUNNER, contract.CHILD):
            source = (ROOT / relative).read_text(encoding="utf-8")
            tree = ast.parse(source)
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.append(node.module or "")
            self.assertFalse(any("evaluate_v24923" in name for name in imports))
            self.assertNotIn("evaluation/", source)


if __name__ == "__main__":
    unittest.main()
