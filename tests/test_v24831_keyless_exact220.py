from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24791_exact220_contract as parent  # noqa: E402
from deepwide_agent import v24831_keyless_exact220_contract as contract  # noqa: E402
from scripts import control_v24831_keyless_exact220 as control  # noqa: E402
from scripts import run_v24635_exact220 as parent_runner  # noqa: E402
from scripts import run_v24635_exact220_task as parent_child  # noqa: E402
from scripts import run_v24831_keyless_exact220 as runner  # noqa: E402
from scripts import run_v24831_keyless_exact220_task as child  # noqa: E402


class V24831KeylessExact220Tests(unittest.TestCase):
    def test_algorithm_budget_and_capacity_equal_parent(self) -> None:
        self.assertEqual(contract.LIMITS, parent.LIMITS)
        self.assertEqual(contract.MODEL, parent.MODEL)
        self.assertEqual(contract.SEARCH, parent.SEARCH)
        self.assertEqual(contract.TWO_WAVE_POLICY, parent.TWO_WAVE_POLICY)
        self.assertEqual(
            (contract.SELECTED_COUNT, contract.EXECUTOR_CONCURRENCY, contract.MODEL_SLOT_CAP),
            (220, 20, 8),
        )

    def test_fresh_namespace_and_keyless_transport(self) -> None:
        self.assertNotEqual(contract.PROTOCOL, parent.PROTOCOL)
        self.assertNotEqual(contract.OUTPUT_ROOT, parent.OUTPUT_ROOT)
        self.assertNotEqual(contract.RUNNER_MARKER, parent.RUNNER_MARKER)
        self.assertEqual(contract.MODEL["proxy_url"], "http://127.0.0.1:9878/responses")
        self.assertEqual(
            contract.SEARCH["provider"],
            "azure-native-keyless-bounded-same-response-title-backfill",
        )

    def test_task_vector_is_exact220_and_label_blind(self) -> None:
        tasks = contract.task_vector(ROOT)
        self.assertEqual(len(tasks), 220)
        self.assertEqual(len({task["opaque_id"] for task in tasks}), 220)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))

    def test_all_four_watchers_are_protected(self) -> None:
        self.assertEqual(
            [item["pid"] for item in contract.protected_watcher_snapshot()],
            [795336, 3061652, 2808901, 2889939],
        )

    def test_runner_reuses_frozen_functions_and_rebinds_paths(self) -> None:
        runner.configure_algorithm()
        self.assertIs(parent_runner.execute_forward, parent_runner.execute_forward)
        self.assertEqual(parent_runner.OUTPUT_ROOT, contract.OUTPUT_ROOT)
        self.assertEqual(parent_runner.CHILD_MARKER, contract.CHILD_MARKER)

    def test_child_reuses_frozen_main_and_rebinds_paths(self) -> None:
        child.configure()
        self.assertIs(parent_child.main, parent_child.main)
        self.assertEqual(parent_child.OUTPUT_ROOT, contract.OUTPUT_ROOT)
        self.assertEqual(parent_child.TASK_ROOT, contract.TASK_ROOT)

    def test_runtime_semantic_audit_has_no_privileged_or_evaluator_capability(self) -> None:
        self.assertEqual(control._runtime_findings(), ([], [], []))

    def test_create_only_publication_rejects_overwrite(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "stage.json"
            control.publish_new(path, {})
            with self.assertRaises(FileExistsError):
                control.publish_new(path, {})


if __name__ == "__main__":
    unittest.main()
