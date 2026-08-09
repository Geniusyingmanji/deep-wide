from __future__ import annotations

import ast
import hashlib
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24942_compact_schema_bound_record_ledger as baseline  # noqa: E402
from deepwide_agent import v24945_injective_schema_signature_ledger as candidate  # noqa: E402
from deepwide_agent import v24947_native_layout_signature_external_contract as contract  # noqa: E402
from scripts import evaluate_v24940_open_world_ledger_external as evaluator_base  # noqa: E402
from scripts import evaluate_v24947_native_layout_signature_external as evaluator  # noqa: E402
from scripts import run_v24947_native_layout_signature_external as runner  # noqa: E402
from scripts import run_v24947_native_layout_signature_external_task as task_runner  # noqa: E402
from scripts.run_v24941_open_world_ledger_external_task import select_task_page  # noqa: E402
from tests.test_v24940_open_world_ledger_external import catalog_blob, target_blob  # noqa: E402


class V24947NativeLayoutSignatureExternalTests(unittest.TestCase):
    def snapshot(self):
        return runner.build_snapshot(catalog_blob(), [target_blob()])

    def test_target_is_fresh_and_fixed(self) -> None:
        self.assertEqual(contract.TARGET_KEYS, ("SP.POP.TOTL@2019",))
        self.assertTrue(set(contract.TARGET_KEYS).isdisjoint(contract.DEVELOPMENT_TARGET_KEYS))
        self.assertEqual((contract.SELECTED_COUNT, contract.SELECTED_RECORD_COUNT), (18, 152))

    def test_snapshot_uses_production_native_html_layout(self) -> None:
        bundle, tasks, freeze = self.snapshot()
        self.assertTrue(bundle["native_html_rendered_then_production_html_to_text"])
        self.assertTrue(freeze["native_html_to_text_completed_before_arm_branch"])
        self.assertEqual(len(bundle["pages"]), 18)
        header = bundle["pages"][0]["content"].splitlines()[0].split(" | ")
        self.assertEqual(header[:4], contract.native_page_columns())
        self.assertEqual(len(tasks), 18)

    def test_exact_baseline_is_zero_and_signature_candidate_is_nonzero(self) -> None:
        bundle, tasks, _freeze = self.snapshot()
        pages = select_task_page(tasks[0]["question"], bundle["pages"])
        values = task_runner.build_projections(tasks[0]["question"], pages)
        parent = values["parent_30k"]["receipt"]
        treatment = values["target_value_30k"]["receipt"]
        self.assertEqual(parent["policy_id"], baseline.POLICY_ID)
        self.assertEqual(parent["admissible_bound_observation_count"], 0)
        self.assertEqual(treatment["policy_id"], candidate.POLICY_ID)
        self.assertEqual(treatment["signature_header_bound_table_count"], 1)
        self.assertEqual(treatment["discovered_row_key_count"], 16)
        self.assertEqual(treatment["admissible_bound_observation_count"], 48)
        self.assertEqual(treatment["retained_admissible_bound_observation_count"], 48)

    def test_projection_change_preserves_same_page_and_budget(self) -> None:
        bundle, tasks, _freeze = self.snapshot()
        pages = select_task_page(tasks[0]["question"], bundle["pages"])
        values = task_runner.build_projections(tasks[0]["question"], pages)
        self.assertNotEqual(values["parent_30k"]["projection"], values["target_value_30k"]["projection"])
        self.assertLessEqual(len(values["parent_30k"]["projection"]), 30_000)
        self.assertLessEqual(len(values["target_value_30k"]["projection"]), 30_000)

    def test_tasks_are_row_blind_and_bind_one_page(self) -> None:
        bundle, tasks, _freeze = self.snapshot()
        for task in tasks:
            self.assertEqual(set(task), {"opaque_id", "question"})
            self.assertNotIn("<ENTITIES>", task["question"])
            self.assertNotIn("<COUNTRIES>", task["question"])
            self.assertEqual(len(select_task_page(task["question"], bundle["pages"])), 1)

    def test_evaluator_maps_native_headers_only_after_freeze(self) -> None:
        bundle, tasks, _freeze = self.snapshot()
        rows = evaluator._source_rows(bundle["pages"][0])
        self.assertEqual(len(rows), 16)
        self.assertEqual(list(rows[0]), contract.visible_columns())
        gold = evaluator.build_gold(tasks, bundle)
        self.assertEqual(len(gold), 18)
        self.assertTrue(all(len(value) == 8 for value in gold.values()))

    def test_evaluator_exact_metric_accepts_visible_schema(self) -> None:
        columns = contract.visible_columns()
        gold = [{columns[0]: "Alpha", columns[1]: "C01", columns[2]: "ALP", columns[3]: "12"}]
        table = "| " + " | ".join(columns) + " |\n| " + " | ".join("---" for _ in columns) + " |\n"
        table += "| Alpha | C01 | ALP | 12 |"
        self.assertEqual(evaluator.evaluate_prediction(table, gold)["exact_table_success"], 1)

    def test_arm_order_is_counterbalanced_and_deterministic(self) -> None:
        orders = {contract.arm_order("task_" + f"{index:024x}") for index in range(32)}
        self.assertEqual(orders, {contract.ARMS, contract.ARMS[::-1]})

    def test_runtime_boundary_is_label_blind_and_evaluator_absent(self) -> None:
        self.assertNotIn(contract.EVALUATOR, contract.RUNTIME_SOURCES)
        privileged = {"category", "question_type", "task_category", "split", "ground_truth", "gold", "answer_key", "mapping", "evaluator", "score", "reward"}
        for relative in contract.RUNTIME_SOURCES:
            source = (ROOT / relative).read_text(encoding="utf-8")
            tree = ast.parse(source)
            hits = []
            for node in ast.walk(tree):
                key = None
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {"get", "pop", "setdefault"} and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    key = node.args[0].value.casefold()
                elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
                    key = node.slice.value.casefold()
                if key in privileged:
                    hits.append((node.lineno, key))
            self.assertEqual(hits, [], str(relative))

    def test_duplicate_cohort_and_extra_runtime_key_fail_closed(self) -> None:
        cohort = runner._cohorts()[0]
        question = (
            f"Include every record whose Cohort is {cohort}. Do not include other cohorts.\n"
            "Column names: " + " | ".join(contract.visible_columns()) + f"\nCohort is {cohort}."
        )
        tasks = [
            {"opaque_id": "task_" + hashlib.sha256(str(index).encode()).hexdigest()[:24], "question": question}
            for index in range(contract.SELECTED_COUNT)
        ]
        with self.assertRaises(ValueError):
            contract.validate_task_vector(tasks)
        tasks[0]["extra"] = "bad"
        with self.assertRaises(ValueError):
            contract.validate_task_vector(tasks)


if __name__ == "__main__":
    unittest.main()
