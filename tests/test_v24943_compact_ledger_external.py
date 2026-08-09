from __future__ import annotations

import ast
import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path: sys.path.insert(0, str(path))

from deepwide_agent import v24940_open_world_ledger_external_contract as original  # noqa: E402
from deepwide_agent import v24943_compact_ledger_external_contract as contract  # noqa: E402
from deepwide_agent import v24939_schema_bound_record_ledger as verbose  # noqa: E402
from deepwide_agent import v24942_compact_schema_bound_record_ledger as compact  # noqa: E402
from scripts import run_v24923_target_value_external as engine  # noqa: E402
from scripts import run_v24940_open_world_ledger_external as population  # noqa: E402
from scripts import run_v24943_compact_ledger_external as runner  # noqa: E402
from scripts import run_v24943_compact_ledger_external_task as task_runner  # noqa: E402
from tests.test_v24940_open_world_ledger_external import catalog_blob, target_blob  # noqa: E402


class V24943CompactLedgerExternalTests(unittest.TestCase):
    def tearDown(self) -> None:
        population.contract = original; engine.contract = original

    def snapshot(self):
        runner.configure(); return population.build_snapshot(catalog_blob(), [target_blob()])

    def test_fresh_target_and_population_are_fixed(self) -> None:
        self.assertEqual(contract.TARGET_KEYS, ("SP.POP.TOTL@2020",)); self.assertNotIn(contract.TARGET_KEYS[0], contract.DEVELOPMENT_TARGET_KEYS)
        self.assertEqual((contract.SELECTED_COUNT, contract.SELECTED_RECORD_COUNT), (18, 152))

    def test_snapshot_tasks_are_row_blind_and_page_bound(self) -> None:
        bundle, tasks, _freeze = self.snapshot(); self.assertEqual(len(tasks), 18)
        for task in tasks: self.assertNotIn("<ENTITIES>", task["question"])
        from scripts.run_v24941_open_world_ledger_external_task import select_task_page
        self.assertEqual(len(select_task_page(tasks[0]["question"], bundle["pages"])), 1)

    def test_only_projection_representation_differs(self) -> None:
        bundle, tasks, _freeze = self.snapshot()
        from scripts.run_v24941_open_world_ledger_external_task import select_task_page
        page = select_task_page(tasks[0]["question"], bundle["pages"])
        values = task_runner.build_projections(tasks[0]["question"], page)
        base = values["parent_30k"]["receipt"]; cand = values["target_value_30k"]["receipt"]
        self.assertEqual(base["admissible_bound_observation_count"], cand["admissible_bound_observation_count"])
        self.assertEqual(base["discovered_row_key_count"], cand["discovered_row_key_count"])
        self.assertEqual(base["policy_id"], verbose.POLICY_ID); self.assertEqual(cand["policy_id"], compact.POLICY_ID)
        self.assertGreater(cand["retained_admissible_bound_observation_count"], base["retained_admissible_bound_observation_count"])

    def test_compact_candidate_reaches_full_retention(self) -> None:
        bundle, tasks, _freeze = self.snapshot()
        from scripts.run_v24941_open_world_ledger_external_task import select_task_page
        values = task_runner.build_projections(tasks[0]["question"], select_task_page(tasks[0]["question"], bundle["pages"]))
        receipt = values["target_value_30k"]["receipt"]
        self.assertEqual(receipt["admissible_bound_observation_count"], 48); self.assertEqual(receipt["retained_admissible_bound_observation_count"], 48)

    def test_arm_order_is_deterministic_counterbalanced(self) -> None:
        orders = {contract.arm_order("task_" + f"{index:024x}") for index in range(32)}; self.assertEqual(orders, {contract.ARMS, contract.ARMS[::-1]})

    def test_runtime_is_label_blind_and_evaluator_absent(self) -> None:
        self.assertNotIn(contract.EVALUATOR, contract.RUNTIME_SOURCES)
        privileged = {"category", "question_type", "task_category", "split", "ground_truth", "gold", "answer_key", "mapping", "evaluator", "score", "reward"}
        for relative in contract.RUNTIME_SOURCES:
            source = (ROOT / relative).read_text(encoding="utf-8"); tree = ast.parse(source); hits=[]
            for node in ast.walk(tree):
                key=None
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {"get","pop","setdefault"} and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value,str): key=node.args[0].value.casefold()
                elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value,str): key=node.slice.value.casefold()
                if key in privileged: hits.append((node.lineno,key))
            self.assertEqual(hits, [], str(relative))

    def test_visible_task_vector_rejects_duplicate_cohort(self) -> None:
        cohort="C01"; question=f"Include every record whose Cohort is {cohort}. Do not include other cohorts.\nColumn names: " + " | ".join(contract.visible_columns()) + f"\nPredicate {cohort}."
        tasks=[{"opaque_id":"task_"+hashlib.sha256(str(i).encode()).hexdigest()[:24],"question":question} for i in range(18)]
        with self.assertRaises(ValueError): contract.validate_task_vector(tasks)


if __name__ == "__main__": unittest.main()
