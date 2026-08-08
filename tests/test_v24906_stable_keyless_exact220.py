from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24831_keyless_exact220_contract as parent  # noqa: E402
from deepwide_agent import v24906_stable_keyless_exact220_contract as contract  # noqa: E402
from scripts import control_v24906_stable_keyless_exact220 as control  # noqa: E402
from scripts import finalize_v24906_stable_keyless_exact220 as finalizer  # noqa: E402
from scripts import run_v24635_exact220 as algorithm  # noqa: E402
from scripts import run_v24635_exact220_task as task_algorithm  # noqa: E402
from scripts import run_v24906_stable_keyless_exact220 as runner  # noqa: E402
from scripts import run_v24906_stable_keyless_exact220_task as child  # noqa: E402


class V24906StableKeylessExact220Tests(unittest.TestCase):
    def test_algorithm_budget_and_capacity_equal_stable_parent(self) -> None:
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

    def test_runner_reuses_stable_functions_and_rebinds_paths(self) -> None:
        runner.configure()
        runner.base.configure_algorithm()
        self.assertEqual(algorithm.OUTPUT_ROOT, contract.OUTPUT_ROOT)
        self.assertEqual(algorithm.CHILD_MARKER, contract.CHILD_MARKER)

    def test_child_reuses_stable_main_and_rebinds_paths(self) -> None:
        child.configure()
        child.base.configure()
        self.assertIs(task_algorithm.main, task_algorithm.main)
        self.assertEqual(task_algorithm.OUTPUT_ROOT, contract.OUTPUT_ROOT)
        self.assertEqual(task_algorithm.TASK_ROOT, contract.TASK_ROOT)

    def test_runtime_semantic_audit_has_no_privileged_or_evaluator_capability(self) -> None:
        control.configure()
        self.assertEqual(control.base._runtime_findings(), ([], [], []))

    def test_finalizer_and_create_only_surfaces_are_fresh(self) -> None:
        finalizer.configure()
        self.assertIn("v24906_stable_keyless", str(finalizer.parent.base.FINAL_RESULT))
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "stage.json"
            control.base.publish_new(path, {})
            with self.assertRaises(FileExistsError):
                control.base.publish_new(path, {})


if __name__ == "__main__":
    unittest.main()
