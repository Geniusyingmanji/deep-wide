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

from deepwide_agent import v24941_open_world_ledger_external_contract as contract  # noqa: E402
from deepwide_agent import v24940_open_world_ledger_external_contract as parent_contract  # noqa: E402
from scripts import run_v24923_target_value_external as engine  # noqa: E402
from scripts import run_v24940_open_world_ledger_external as builder  # noqa: E402
from scripts import run_v24940_open_world_ledger_external_task as projector  # noqa: E402
from scripts import run_v24941_open_world_ledger_external as runner  # noqa: E402
from scripts import run_v24941_open_world_ledger_external_task as task_runner  # noqa: E402
from tests.test_v24940_open_world_ledger_external import catalog_blob, target_blob  # noqa: E402


class V24941OpenWorldLedgerExternalTests(unittest.TestCase):
    def tearDown(self) -> None:
        # V2.49.41 deliberately configures inherited modules at process scope;
        # restore their parent bindings so an aggregate test process remains
        # order-independent.
        builder.contract = parent_contract
        engine.contract = parent_contract
        projector.contract = parent_contract
        projector.base.contract = parent_contract

    def test_fresh_target_population_and_capacity_are_frozen(self) -> None:
        self.assertEqual(contract.TARGET_KEYS, ("SP.POP.TOTL@2021",))
        self.assertNotIn(contract.TARGET_KEYS[0], contract.DEVELOPMENT_TARGET_KEYS)
        self.assertEqual(contract.SELECTED_COUNT, 18)
        self.assertEqual(contract.SELECTED_RECORD_COUNT, 152)
        self.assertLess(contract.SELECTED_RECORD_COUNT, 196)

    def test_snapshot_has_18_tasks_and_page_alignment(self) -> None:
        runner.configure()
        bundle, tasks, freeze = builder.build_snapshot(catalog_blob(), [target_blob()])
        self.assertEqual(len(bundle["pages"]), contract.SELECTED_COUNT)
        self.assertEqual(len(tasks), contract.SELECTED_COUNT)
        self.assertEqual(freeze["selected_records"], contract.SELECTED_RECORD_COUNT)
        for task, expected in zip(tasks, bundle["pages"], strict=True):
            self.assertEqual(
                task_runner.select_task_page(task["question"], bundle["pages"]),
                [expected],
            )

    def test_page_alignment_rejects_missing_or_ambiguous_cohort(self) -> None:
        runner.configure()
        bundle, tasks, _freeze = builder.build_snapshot(catalog_blob(), [target_blob()])
        with self.assertRaises(RuntimeError):
            task_runner.select_task_page(tasks[0]["question"], bundle["pages"][1:])
        duplicate = [bundle["pages"][0], dict(bundle["pages"][0])]
        with self.assertRaises(RuntimeError):
            task_runner.select_task_page(tasks[0]["question"], duplicate)

    def test_candidate_projection_on_aligned_page_discovers_all_rows(self) -> None:
        runner.configure()
        bundle, tasks, _freeze = builder.build_snapshot(catalog_blob(), [target_blob()])
        page = task_runner.select_task_page(tasks[0]["question"], bundle["pages"])
        projector.contract = contract
        value = projector.build_projections(tasks[0]["question"], page)
        receipt = value["target_value_30k"]["receipt"]
        self.assertEqual(receipt["discovered_row_key_count"], contract.PAGE_ROWS_PER_TASK)
        self.assertGreaterEqual(
            receipt["retained_admissible_bound_observation_count"],
            contract.ROWS_PER_TASK * 3,
        )

    def test_task_vector_has_no_entity_enumeration(self) -> None:
        tasks = []
        for index, cohort in enumerate(builder._cohorts()[: contract.SELECTED_COUNT]):
            tasks.append({
                "opaque_id": "task_" + hashlib.sha256(str(index).encode()).hexdigest()[:24],
                "question": f"Include every record whose Cohort is {cohort}. Do not include other cohorts.\nColumn names: " + " | ".join(contract.visible_columns()) + f"\nCohort predicate is {cohort}.",
            })
        validated = contract.validate_task_vector(tasks)
        self.assertTrue(all("<ENTITIES>" not in row["question"] for row in validated))

    def test_runtime_sources_are_label_blind_and_evaluator_absent(self) -> None:
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


if __name__ == "__main__":
    unittest.main()
