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

from deepwide_agent import v24934_contextual_record_external_contract as contract  # noqa: E402
from scripts import evaluate_v24934_contextual_record_external as evaluator_wrapper  # noqa: E402
from scripts import run_v24934_contextual_record_external as runner  # noqa: E402
from scripts import run_v24934_contextual_record_external_task as child  # noqa: E402


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
            "name": f"Synthetic Entity Name {index:03d}",
            "region": {"id": "TST"},
        }
        for index in range(220)
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


class V24934ContextualRecordExternalTests(unittest.TestCase):
    def test_confirmatory_targets_are_fixed_and_prior_targets_disjoint(self) -> None:
        self.assertEqual(len(contract.TARGETS), 2)
        self.assertTrue(
            set(contract.TARGET_KEYS).isdisjoint(contract.DEVELOPMENT_TARGET_KEYS)
        )

    def test_task_vector_is_24x8_and_label_blind(self) -> None:
        catalog_blob, target_blobs = synthetic_snapshot()
        bundle, tasks, freeze = runner.build_snapshot(catalog_blob, target_blobs)
        self.assertEqual(len(tasks), 24)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))
        self.assertTrue(
            all(len(contract.parse_visible_entities(task["question"])) == 8 for task in tasks)
        )
        self.assertEqual(len(bundle["pages"]), 2)
        self.assertEqual(freeze["selected_entities"], 192)
        self.assertEqual(
            {contract.arm_order(task["opaque_id"]) for task in tasks},
            {contract.ARMS, contract.ARMS[::-1]},
        )

    def test_snapshot_representation_is_ordinary_text_and_shared(self) -> None:
        catalog_blob, target_blobs = synthetic_snapshot()
        bundle, _tasks, _freeze = runner.build_snapshot(catalog_blob, target_blobs)
        self.assertTrue(bundle["same_page_vector_for_both_arms"])
        self.assertTrue(bundle["page_representation_fixed_before_arm_branch"])
        for page in bundle["pages"]:
            self.assertIn("# Country coverage index", page["content"])
            self.assertIn("official observations", page["content"])
            self.assertNotIn("| Country |", page["content"])
            self.assertGreater(len(page["content"]), 8_000)

    def test_both_arms_use_same_30k_and_5k_caps(self) -> None:
        catalog_blob, target_blobs = synthetic_snapshot()
        bundle, tasks, _freeze = runner.build_snapshot(catalog_blob, target_blobs)
        values = child.build_projections(tasks[0]["question"], bundle["pages"])
        for arm in contract.ARMS:
            policy = values[arm]["receipt"]["policy"]
            self.assertEqual(policy["total_character_cap"], 30_000)
            self.assertEqual(policy["maximum_page_chars"], 5_000)

    def test_contextual_mechanism_engages_and_projection_changes(self) -> None:
        catalog_blob, target_blobs = synthetic_snapshot()
        bundle, tasks, _freeze = runner.build_snapshot(catalog_blob, target_blobs)
        values = child.build_projections(tasks[0]["question"], bundle["pages"])
        candidate = values["target_value_30k"]["receipt"]
        self.assertNotEqual(
            values["parent_30k"]["projection"],
            values["target_value_30k"]["projection"],
        )
        self.assertGreater(candidate["supported_contextual_target_value_pair_count"], 0)
        self.assertGreater(candidate["retained_contextual_target_value_pair_count"], 0)
        self.assertFalse(candidate["entropy_or_information_gain_assigns_credit"])

    def test_prompt_has_no_evaluator_or_ground_truth(self) -> None:
        prompt = child._prompt("VISIBLE QUESTION", "VISIBLE EVIDENCE")
        self.assertIn("VISIBLE QUESTION", prompt)
        self.assertIn("VISIBLE EVIDENCE", prompt)
        self.assertNotIn("ground_truth", prompt)
        self.assertNotIn("evaluator", prompt)

    def test_evaluator_exact_table(self) -> None:
        evaluator_wrapper.configure()
        catalog_blob, target_blobs = synthetic_snapshot()
        bundle, tasks, _freeze = runner.build_snapshot(catalog_blob, target_blobs)
        gold = evaluator_wrapper.base.build_gold(tasks, bundle)
        opaque = tasks[0]["opaque_id"]
        columns = contract.visible_columns()
        lines = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
        for row in gold[opaque]:
            lines.append(
                "| "
                + " | ".join(
                    row["Country"] if index == 0 else row[column]
                    for index, column in enumerate(columns)
                )
                + " |"
            )
        metric = evaluator_wrapper.base.evaluate_prediction("\n".join(lines), gold[opaque])
        self.assertEqual(metric["exact_table_success"], 1)
        self.assertEqual(metric["composite"], 1.0)

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
            self.assertFalse(any("evaluate_v24934" in name for name in imports))
            self.assertNotIn("evaluation/", source)


if __name__ == "__main__":
    unittest.main()
