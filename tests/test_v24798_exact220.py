from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24798_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24796_deadline_tavily_search import empty_receipt, validate_receipt  # noqa: E402
from scripts import control_v24798_exact220 as control  # noqa: E402
from scripts import run_v24798_exact220 as runner  # noqa: E402
from scripts import run_v24798_exact220_task as child  # noqa: E402
from scripts import run_v24635_exact220 as parent_runner  # noqa: E402
from scripts import run_v24635_exact220_task as parent_child  # noqa: E402


class V24798Exact220Tests(unittest.TestCase):
    def test_parent_and_visible_exact220_are_current_and_label_blind(self) -> None:
        parent = contract.parent_contract(ROOT)
        tasks = contract.task_vector(ROOT)
        self.assertEqual(parent["protocol_id"], "v24791_fresh_v24635_runtime_exact220_v1")
        self.assertEqual(len(tasks), 220)
        self.assertEqual(len({task["opaque_id"] for task in tasks}), 220)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))

    def test_successor_keeps_budget_and_uses_validated_direct_transport(self) -> None:
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, 20)
        self.assertEqual(contract.MODEL_SLOT_CAP, 8)
        self.assertEqual(contract.TAVILY_KEY_SLOT_CAP, 12)
        self.assertEqual(contract.LIMITS["wall_seconds"], 240)
        self.assertEqual(contract.LIMITS["search_queries"], 4)
        self.assertFalse(contract.SEARCH["provider_content_forwarded"])
        smoke = contract.validate_smoke(ROOT)
        self.assertEqual(smoke["successful_query_rows"], 12)
        self.assertGreaterEqual(smoke["usable_fetched_pages"], 12)
        self.assertEqual(
            {item["pid"] for item in contract.protected_watcher_snapshot()},
            {795336, 3061652, 2808901, 2889939},
        )

    def test_protocol_is_fresh_and_excludes_prior_outputs(self) -> None:
        value = contract.build_protocol(ROOT, now=1, require_clean=False, require_pristine=False)
        self.assertEqual(value["task_contract"]["selected_count"], 220)
        self.assertEqual(value["execution"]["output_root"], str(contract.OUTPUT_ROOT))
        self.assertFalse(value["parent_algorithm"]["prior_output_prediction_result_score_or_evaluator_read_or_reused"])
        self.assertFalse(any(path.startswith("outputs/") for path in value["dependency_manifest"]))
        self.assertNotIn("scripts/run_official_eval_local.py", value["dependency_manifest"])

    def test_runner_reuses_frozen_scheduler_and_rebinds_validation(self) -> None:
        keys = tuple(f"synthetic-key-{index:02d}" for index in range(12))
        runner.configure_algorithm(keys)
        self.assertIs(runner.algorithm.execute_forward, parent_runner.execute_forward)
        self.assertEqual(parent_runner.OUTPUT_ROOT, contract.OUTPUT_ROOT)
        self.assertEqual(parent_runner.CHILD_MARKER, contract.CHILD_MARKER)
        self.assertIs(parent_runner._validate_bundle, runner._validate_bundle)

    def test_runner_reads_exact_credentials_from_stdin_without_emitting(self) -> None:
        keys = tuple(f"synthetic-key-{index:02d}" for index in range(12))
        self.assertEqual(runner._read_credentials(io.StringIO("\n".join(keys))), keys)
        with self.assertRaises(RuntimeError):
            runner._read_credentials(io.StringIO("\n".join(keys[:11])))

    def test_child_pops_environment_credential(self) -> None:
        keys = tuple(f"synthetic-key-{index:02d}" for index in range(12))
        with patch.dict(os.environ, {"TAVILY_API_KEYS": "\n".join(keys)}, clear=False):
            self.assertEqual(child._credentials_from_environment(), keys)
            self.assertNotIn("TAVILY_API_KEYS", os.environ)

    def test_child_wrapper_rebinds_direct_search(self) -> None:
        keys = tuple(f"synthetic-key-{index:02d}" for index in range(12))
        argv = ["child", "--result", str(ROOT / contract.TASK_ROOT / "task_0001" / "result.json")]
        with patch.dict(os.environ, {"TAVILY_API_KEYS": "\n".join(keys)}, clear=False):
            directory = child.configure(argv)
        self.assertEqual(directory.name, "task_0001")
        self.assertEqual(parent_child.OUTPUT_ROOT, contract.OUTPUT_ROOT)

    def test_empty_receipt_is_valid_and_content_free(self) -> None:
        value = validate_receipt(empty_receipt(12))
        self.assertEqual(value["key_slot_cap"], 12)
        self.assertEqual(value["provider_attempts"], 0)
        self.assertFalse(value["credential_value_persisted_hashed_emitted_or_in_error"])

    def test_direct_summary_aggregates_only_counts(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            root = Path(directory)
            old_root = contract.TASK_ROOT
            contract.TASK_ROOT = Path("tasks")
            try:
                for position in range(1, 221):
                    target = root / "tasks" / f"task_{position:04d}"
                    target.mkdir(parents=True)
                    parent_runner._new_json(target / contract.DIRECT_RECEIPT_NAME, empty_receipt(12))
                value = runner._direct_search_totals(root)
            finally:
                contract.TASK_ROOT = old_root
        self.assertEqual(value["valid_receipts"], 220)
        self.assertEqual(value["provider_attempts"], 0)

    def test_progress_is_content_free_fixed_denominator(self) -> None:
        value = runner._progress(17)
        self.assertEqual(value["selected"], 220)
        self.assertEqual(value["completed"], 17)
        self.assertEqual(value["unfinished"], 203)
        self.assertFalse(value["contains_question_query_url_page_prediction_answer_opaque_id_or_credential"])

    def test_runtime_semantic_audit_has_no_privileged_or_evaluator_capability(self) -> None:
        self.assertEqual(control._runtime_findings(), ([], [], []))

    def test_preaudit_authority_and_create_only_publication(self) -> None:
        self.assertEqual(sum(count for _path, count, _timeout in control.TEST_SUITES), control.EXPECTED_TESTS)
        self.assertFalse(control.PREAUDIT_AUTH["single_fresh_exact220_forward"])
        self.assertTrue(control.START_AUTH["single_fresh_exact220_forward"])
        source = Path(control.__file__).read_text(encoding="utf-8")
        self.assertIn('choices=("protocol", "audit", "start")', source)
        self.assertNotIn('"evaluate"', source)
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "stage.json"
            control.publish_new(path, {})
            with self.assertRaises(FileExistsError):
                control.publish_new(path, {})


if __name__ == "__main__":
    unittest.main()
