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

from deepwide_agent import v24937_layout_diverse_contextual_external_contract as contract  # noqa: E402
from scripts import evaluate_v24937_layout_diverse_contextual_external as evaluator  # noqa: E402
from scripts import run_v24937_layout_diverse_contextual_external as runner  # noqa: E402
from scripts import run_v24934_contextual_record_external_task as projector_child  # noqa: E402


def synthetic_snapshot() -> tuple[bytes, list[bytes]]:
    def iso3(index: int) -> str:
        return "".join((chr(65 + (index // 676) % 26), chr(65 + (index // 26) % 26), chr(65 + index % 26)))
    catalog = [{"id": iso3(index), "name": f"Synthetic Entity {index:03d}", "region": {"id": "TST"}} for index in range(220)]
    blobs = []
    for target_index in range(2):
        rows = [{"country": {"value": item["name"]}, "countryiso3code": item["id"], "value": f"{target_index + 1}.{index:03d}"} for index, item in enumerate(catalog)]
        blobs.append(json.dumps([{}, rows]).encode())
    return json.dumps([{}, catalog]).encode(), blobs


class V24937LayoutDiverseContextualExternalTests(unittest.TestCase):
    def test_target_keys_are_new_and_fixed_at_boundary(self) -> None:
        self.assertEqual(set(contract.TARGET_KEYS), {"SP.RUR.TOTL.ZS@2022", "IT.CEL.SETS.P2@2022"})
        self.assertTrue(set(contract.TARGET_KEYS).isdisjoint(contract.DEVELOPMENT_TARGET_KEYS))
        self.assertEqual(contract.HISTORICAL_BOUNDARY_COMMIT, "4ece134")

    def test_two_distinct_ordinary_text_layouts(self) -> None:
        catalog, blobs = synthetic_snapshot()
        bundle, _tasks, freeze = runner.build_snapshot(catalog, blobs)
        self.assertEqual(bundle["layout_vector"], ["markdown_heading_colon_records", "plain_target_label_bullet_equals_records"])
        self.assertEqual(bundle["layout_vector"], freeze["layout_vector"])
        self.assertIn("# Rural population", bundle["pages"][0]["content"])
        self.assertIn(" official records:\n\n- ", bundle["pages"][1]["content"])

    def test_task_vector_is_24x8_label_blind_and_counterbalanced(self) -> None:
        catalog, blobs = synthetic_snapshot()
        _bundle, tasks, _freeze = runner.build_snapshot(catalog, blobs)
        self.assertEqual(len(tasks), 24)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))
        self.assertTrue(all(len(contract.parse_visible_entities(task["question"])) == 8 for task in tasks))
        self.assertEqual({contract.arm_order(task["opaque_id"]) for task in tasks}, {contract.ARMS, contract.ARMS[::-1]})

    def test_both_layouts_create_contextual_pairs(self) -> None:
        catalog, blobs = synthetic_snapshot()
        bundle, tasks, _freeze = runner.build_snapshot(catalog, blobs)
        projector_child.contract = contract
        values = projector_child.build_projections(tasks[0]["question"], bundle["pages"])
        receipt = values["target_value_30k"]["receipt"]
        self.assertGreaterEqual(receipt["supported_contextual_target_value_pair_count"], 16)
        self.assertGreaterEqual(receipt["retained_contextual_target_value_pair_count"], 16)
        self.assertNotEqual(values["parent_30k"]["projection"], values["target_value_30k"]["projection"])

    def test_same_caps_and_no_entropy_credit(self) -> None:
        catalog, blobs = synthetic_snapshot()
        bundle, tasks, _freeze = runner.build_snapshot(catalog, blobs)
        projector_child.contract = contract
        values = projector_child.build_projections(tasks[0]["question"], bundle["pages"])
        for arm in contract.ARMS:
            self.assertEqual(values[arm]["receipt"]["policy"]["total_character_cap"], 30000)
            self.assertEqual(values[arm]["receipt"]["policy"]["maximum_page_chars"], 5000)
            self.assertFalse(values[arm]["receipt"]["entropy_or_information_gain_assigns_credit"])

    def test_corrected_evaluator_accepts_matching_visible_iso3(self) -> None:
        entities = [("Alpha", "ALP")]
        columns = contract.visible_columns()
        gold = [{"Country": "Alpha", columns[1]: "1", columns[2]: "2"}]
        prediction = "| " + " | ".join(columns) + " |\n|---|---:|---:|\n| Alpha [ALP] | 1 | 2 |"
        metric = evaluator.evaluate_prediction(prediction, gold, entities)
        self.assertEqual(metric["exact_table_success"], 1)

    def test_corrected_evaluator_rejects_wrong_iso3(self) -> None:
        entities = [("Alpha", "ALP")]
        columns = contract.visible_columns()
        gold = [{"Country": "Alpha", columns[1]: "1", columns[2]: "2"}]
        prediction = "| " + " | ".join(columns) + " |\n|---|---:|---:|\n| Alpha [BET] | 1 | 2 |"
        metric = evaluator.evaluate_prediction(prediction, gold, entities)
        self.assertEqual(metric["entity_recall"], 0)
        self.assertEqual(metric["exact_table_success"], 0)

    def test_evaluator_parses_both_frozen_layouts(self) -> None:
        catalog, blobs = synthetic_snapshot()
        bundle, tasks, _freeze = runner.build_snapshot(catalog, blobs)
        gold = evaluator.build_gold(tasks, bundle)
        self.assertEqual(len(gold), 24)
        self.assertTrue(all(len(value["rows"]) == 8 for value in gold.values()))

    def test_forward_runtime_has_no_evaluator_import_or_privileged_access(self) -> None:
        privileged = {"category", "question_type", "ground_truth", "answer_key", "score", "reward"}
        for relative in (contract.RUNNER, contract.CHILD):
            source = (ROOT / relative).read_text(encoding="utf-8")
            tree = ast.parse(source)
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.append(node.module or "")
                key = None
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in {"get", "pop", "setdefault"}
                    and node.args
                    and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)
                ):
                    key = node.args[0].value.casefold()
                elif (
                    isinstance(node, ast.Subscript)
                    and isinstance(node.slice, ast.Constant)
                    and isinstance(node.slice.value, str)
                ):
                    key = node.slice.value.casefold()
                self.assertNotIn(key, privileged)
            self.assertFalse(any("evaluate_v24937" in name for name in imports))


if __name__ == "__main__":
    unittest.main()
