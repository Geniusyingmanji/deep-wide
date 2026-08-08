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

from deepwide_agent import v24925_sparse_target_value_external_contract as contract  # noqa: E402
from scripts import evaluate_v24925_sparse_target_value_external as evaluator  # noqa: E402
from scripts import run_v24925_sparse_target_value_external as runner  # noqa: E402
from scripts import run_v24925_sparse_target_value_external_task as child  # noqa: E402


def iso3(index: int) -> str:
    return "".join(
        (
            chr(65 + (index // (26 * 26)) % 26),
            chr(65 + (index // 26) % 26),
            chr(65 + index % 26),
        )
    )


def synthetic_snapshot() -> tuple[bytes, list[bytes], set[str]]:
    catalog = [
        {"id": iso3(index), "name": f"Country {index:03d}", "region": {"id": "TST"}}
        for index in range(320)
    ]
    targets = []
    for target_index in range(len(contract.TARGETS)):
        targets.append(
            json.dumps(
                [
                    {},
                    [
                        {
                            "country": {"value": item["name"]},
                            "countryiso3code": item["id"],
                            "value": f"{target_index + 1}.{index:03d}",
                        }
                        for index, item in enumerate(catalog)
                    ],
                ]
            ).encode()
        )
    return json.dumps([{}, catalog]).encode(), targets, {iso3(index) for index in range(144)}


class V24925SparseTargetValueExternalTests(unittest.TestCase):
    def test_targets_fixed_four_and_historical_boundary(self) -> None:
        self.assertEqual(len(contract.TARGETS), 4)
        self.assertEqual(len(contract.TARGET_KEYS), 4)
        self.assertEqual(len(contract.HISTORICAL_BOUNDARY_COMMIT), 40)

    def test_population_excludes_all_prior_entities(self) -> None:
        catalog, targets, excluded = synthetic_snapshot()
        _bundle, tasks, freeze = runner.build_snapshot(catalog, targets, excluded)
        selected = {
            iso
            for task in tasks
            for _name, iso in contract.parse_visible_countries(task["question"])
        }
        self.assertTrue(selected.isdisjoint(excluded))
        self.assertEqual(len(selected), 144)
        self.assertEqual(freeze["excluded_prior_entity_count"], 144)

    def test_task_vector_is_label_blind_12x12(self) -> None:
        catalog, targets, excluded = synthetic_snapshot()
        _bundle, tasks, _freeze = runner.build_snapshot(catalog, targets, excluded)
        self.assertEqual(len(tasks), 12)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))
        with self.assertRaises(ValueError):
            contract.validate_task_vector([{**task, "category": "hidden"} for task in tasks])

    def test_both_arms_use_same_30k_and_5k_caps(self) -> None:
        catalog, targets, excluded = synthetic_snapshot()
        bundle, tasks, _freeze = runner.build_snapshot(catalog, targets, excluded)
        projections = child.build_projections(tasks[0]["question"], bundle["pages"])
        for arm in contract.ARMS:
            policy = projections[arm]["projection_receipt"]["policy"]
            self.assertEqual(policy["total_character_cap"], 30_000)
            self.assertEqual(policy["maximum_page_chars"], 5_000)

    def test_sparse_arm_drops_rows_and_reaches_visible_values(self) -> None:
        catalog, targets, excluded = synthetic_snapshot()
        bundle, tasks, _freeze = runner.build_snapshot(catalog, targets, excluded)
        projections = child.build_projections(tasks[0]["question"], bundle["pages"])
        sparse = projections["sparse_target_value_30k"]
        self.assertGreater(sparse["compaction_receipt"]["dropped_table_row_count"], 0)
        self.assertNotEqual(
            projections["target_value_30k"]["projection"], sparse["projection"]
        )
        gold = evaluator.build_gold(tasks, bundle)[tasks[0]["opaque_id"]]
        for row in gold:
            for column in contract.visible_columns()[1:]:
                self.assertIn(row[column], sparse["projection"])

    def test_prompt_has_no_ground_truth_or_evaluator(self) -> None:
        prompt = child._prompt("VISIBLE QUESTION", "VISIBLE EVIDENCE")
        self.assertNotIn("ground_truth", prompt)
        self.assertNotIn("evaluator", prompt)

    def test_evaluator_exact_table(self) -> None:
        catalog, targets, excluded = synthetic_snapshot()
        bundle, tasks, _freeze = runner.build_snapshot(catalog, targets, excluded)
        gold = evaluator.build_gold(tasks, bundle)
        columns = contract.visible_columns()
        opaque = tasks[0]["opaque_id"]
        lines = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
        for row in gold[opaque]:
            lines.append("| " + " | ".join(row[column] for column in columns) + " |")
        metric = evaluator.evaluate_prediction("\n".join(lines), gold[opaque])
        self.assertEqual(metric["exact_table_success"], 1)

    def test_delta_orientation_candidate_minus_parent(self) -> None:
        catalog, targets, excluded = synthetic_snapshot()
        bundle, tasks, _freeze = runner.build_snapshot(catalog, targets, excluded)
        gold = evaluator.build_gold(tasks, bundle)
        rows = []
        columns = contract.visible_columns()
        for task in tasks:
            lines = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
            for row in gold[task["opaque_id"]]:
                lines.append("| " + " | ".join(row[column] for column in columns) + " |")
            exact = "\n".join(lines)
            rows.append({"opaque_id": task["opaque_id"], "predictions": {arm: exact for arm in contract.ARMS}})
        metrics = evaluator.evaluate_rows(rows, gold)
        self.assertEqual(metrics["sparse_target_value_30k_minus_target_value_30k"]["exact_table_successes"], 0)

    def test_entropy_never_assigns_credit(self) -> None:
        catalog, targets, excluded = synthetic_snapshot()
        bundle, tasks, _freeze = runner.build_snapshot(catalog, targets, excluded)
        projections = child.build_projections(tasks[0]["question"], bundle["pages"])
        self.assertFalse(
            projections["sparse_target_value_30k"]["compaction_receipt"][
                "entropy_or_information_gain_assigns_credit"
            ]
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
            self.assertFalse(any("evaluate_v24925" in name for name in imports))
            self.assertNotIn("evaluation/", source)


if __name__ == "__main__":
    unittest.main()
