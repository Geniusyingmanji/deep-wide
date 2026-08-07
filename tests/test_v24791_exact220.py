from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24791_exact220_contract as contract  # noqa: E402
from scripts import control_v24791_exact220 as control  # noqa: E402
from scripts import run_v24791_exact220 as runner  # noqa: E402
from scripts import run_v24791_exact220_task as child  # noqa: E402
from scripts import run_v24635_exact220 as parent_runner  # noqa: E402
from scripts import run_v24635_exact220_task as parent_child  # noqa: E402


class V24791Exact220Tests(unittest.TestCase):
    def test_parent_and_visible_exact220_are_current_and_label_blind(self) -> None:
        parent = contract.parent_contract(ROOT)
        tasks = contract.task_vector(ROOT)
        self.assertEqual(parent["protocol_id"], "v24635_capacity_validated_bounded_title_backfill_exact220_v1")
        self.assertEqual(len(tasks), 220)
        self.assertEqual(len({task["opaque_id"] for task in tasks}), 220)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))

    def test_successor_keeps_validated_capacity_and_budget(self) -> None:
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, 20)
        self.assertEqual(contract.MODEL_SLOT_CAP, 8)
        self.assertEqual(contract.LIMITS["wall_seconds"], 240)
        self.assertEqual(contract.LIMITS["model_calls"], 3)
        self.assertEqual(contract.LIMITS["search_queries"], 4)
        self.assertEqual(contract.LIMITS["fetch_targets"], 10)

    def test_protocol_is_fresh_namespace_and_prior_outputs_are_excluded(self) -> None:
        value = contract.build_protocol(ROOT, now=1, require_clean=False, require_pristine=False)
        self.assertEqual(value["task_contract"]["selected_count"], 220)
        self.assertEqual(value["execution"]["output_root"], str(contract.OUTPUT_ROOT))
        self.assertFalse(value["parent_algorithm"]["prior_output_prediction_result_score_or_evaluator_read_or_reused"])
        self.assertFalse(value["authorization"]["single_fresh_exact220_forward"])
        self.assertFalse(any(path.startswith("outputs/") for path in value["dependency_manifest"]))
        self.assertNotIn("scripts/run_official_eval_local.py", value["dependency_manifest"])

    def test_parent_wrapper_reuses_algorithm_functions_and_rebinds_paths(self) -> None:
        runner.configure_algorithm()
        self.assertIs(runner.algorithm.execute_forward, parent_runner.execute_forward)
        self.assertIs(runner.algorithm.run_one_task, parent_runner.run_one_task)
        self.assertEqual(parent_runner.OUTPUT_ROOT, contract.OUTPUT_ROOT)
        self.assertEqual(parent_runner.CHILD_MARKER, contract.CHILD_MARKER)

    def test_child_wrapper_reuses_frozen_child_main_and_rebinds_paths(self) -> None:
        child.configure()
        self.assertIs(child.algorithm.main, parent_child.main)
        self.assertEqual(parent_child.OUTPUT_ROOT, contract.OUTPUT_ROOT)
        self.assertEqual(parent_child.TASK_ROOT, contract.TASK_ROOT)

    def test_progress_is_content_free_fixed_denominator(self) -> None:
        value = runner._progress(17)
        self.assertEqual(value["selected"], 220)
        self.assertEqual(value["completed"], 17)
        self.assertEqual(value["unfinished"], 203)
        self.assertFalse(value["contains_question_query_url_page_prediction_answer_opaque_id_or_credential"])
        self.assertFalse(value["mapping_gold_category_question_type_split_evaluator_score_reward_read"])

    def test_runtime_semantic_audit_has_no_privileged_or_evaluator_capability(self) -> None:
        self.assertEqual(control._runtime_findings(), ([], [], []))

    def test_preaudit_and_start_authority_are_staged(self) -> None:
        self.assertFalse(control.PREAUDIT_AUTH["single_fresh_exact220_forward"])
        self.assertTrue(control.PREAUDIT_AUTH["execution_start_generation"])
        self.assertTrue(control.START_AUTH["single_fresh_exact220_forward"])
        self.assertFalse(control.START_AUTH["evaluator_call"])
        source = Path(control.__file__).read_text(encoding="utf-8")
        self.assertIn('choices=("protocol", "audit", "start")', source)
        self.assertNotIn('"evaluate"', source)

    def test_create_only_publication_rejects_overwrite(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "stage.json"
            control.publish_new(path, {})
            with self.assertRaises(FileExistsError):
                control.publish_new(path, {})


if __name__ == "__main__":
    unittest.main()
