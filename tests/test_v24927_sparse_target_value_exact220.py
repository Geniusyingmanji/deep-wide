from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24909_keyless_fixed_budget_exact220_contract as parent  # noqa: E402
from deepwide_agent import v24927_sparse_target_value_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24924_visible_row_table_compactor import POLICY_ID  # noqa: E402
from scripts import control_v24927_sparse_target_value_exact220 as control  # noqa: E402
from scripts import finalize_v24927_sparse_target_value_exact220 as finalizer  # noqa: E402
from scripts import run_v24635_exact220 as scheduler  # noqa: E402
from scripts import run_v24635_exact220_task as task_algorithm  # noqa: E402
from scripts import run_v24927_sparse_target_value_exact220 as runner  # noqa: E402
from scripts import run_v24927_sparse_target_value_exact220_task as child  # noqa: E402


QUESTION = """Return a table. Column names: Country | Metric A.
<COUNTRIES>
1. Alpha Republic [ALP]
</COUNTRIES>"""


class V24927SparseTargetValueExact220Tests(unittest.TestCase):
    def test_only_projector_changes_from_parent(self) -> None:
        self.assertEqual(contract.LIMITS, parent.LIMITS)
        self.assertEqual(contract.MODEL, parent.MODEL)
        self.assertEqual(contract.SEARCH, parent.SEARCH)
        self.assertEqual(contract.TWO_WAVE_POLICY, parent.TWO_WAVE_POLICY)

    def test_exact_capacity_and_hard_caps(self) -> None:
        self.assertEqual(
            (contract.SELECTED_COUNT, contract.EXECUTOR_CONCURRENCY, contract.MODEL_SLOT_CAP),
            (220, 20, 8),
        )
        self.assertEqual(
            {name: contract.LIMITS[name] for name in (
                "wall_seconds", "model_calls", "search_queries", "fetch_targets"
            )},
            {"wall_seconds": 240, "model_calls": 3, "search_queries": 4, "fetch_targets": 10},
        )

    def test_fresh_namespace_and_keyless_transport(self) -> None:
        self.assertNotEqual(contract.PROTOCOL, parent.PROTOCOL)
        self.assertNotEqual(contract.OUTPUT_ROOT, parent.OUTPUT_ROOT)
        self.assertEqual(contract.MODEL["proxy_url"], "http://127.0.0.1:9878/responses")

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

    def test_sparse_projection_reaches_late_visible_row(self) -> None:
        filler = "\n".join(f"| filler-{index:03d} | {index} |" for index in range(300))
        batches = [{"results": [{
            "title": "Official",
            "url": "https://example.invalid/data",
            "content": "| Country | Metric A |\n|---|---:|\n" + filler + "\n| Alpha Republic | 991 |",
        }]}]
        child._VISIBLE_QUESTION = QUESTION
        try:
            limits = type("Limits", (), {"page_chars": 5000, "evidence_chars": 30000})()
            projection = child.sparse_target_value_evidence_projection([], batches, limits)
        finally:
            child._VISIBLE_QUESTION = None
            child._LAST_RECEIPT = None
        self.assertIn("991", projection)

    def test_runner_and_child_bind_fresh_policy(self) -> None:
        runner.configure()
        runner.base.configure_algorithm()
        self.assertEqual(scheduler.OUTPUT_ROOT, contract.OUTPUT_ROOT)
        self.assertEqual(scheduler.CHILD_MARKER, contract.CHILD_MARKER)
        child.configure()
        self.assertEqual(task_algorithm.OUTPUT_ROOT, contract.OUTPUT_ROOT)
        self.assertIs(
            child.runtime._evidence_projection,
            child.sparse_target_value_evidence_projection,
        )

    def test_runtime_semantic_audit_has_no_privileged_or_evaluator_capability(self) -> None:
        control.configure()
        self.assertEqual(control.base._runtime_findings(), ([], [], []))

    def test_projector_audit_is_frozen_and_entropy_credit_disabled(self) -> None:
        value = contract._validate_projector_audit(ROOT)
        self.assertTrue(value["audit_valid"])
        self.assertEqual(POLICY_ID, "v24924_visible_row_sparse_table_compactor_v1")
        self.assertFalse(value["source_policy"]["entropy_or_information_gain_assigns_credit"])

    def test_finalizer_and_create_only_surfaces_are_fresh(self) -> None:
        finalizer.configure()
        self.assertIn("v24927_sparse_target_value", str(finalizer.parent.base.FINAL_RESULT))
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "stage.json"
            control.base.publish_new(path, {})
            with self.assertRaises(FileExistsError):
                control.base.publish_new(path, {})


if __name__ == "__main__":
    unittest.main()
