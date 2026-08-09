from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24929_unicode_total_neutral_contract as contract  # noqa: E402
from deepwide_agent.v24928_unicode_total_visible_row_compactor import POLICY_ID  # noqa: E402
from scripts import control_v24929_unicode_total_neutral_gate as control  # noqa: E402
from scripts import run_v24635_exact220 as scheduler  # noqa: E402
from scripts import run_v24635_exact220_task as task_algorithm  # noqa: E402
from scripts import run_v24929_unicode_total_neutral_gate as runner  # noqa: E402
from scripts import run_v24929_unicode_total_neutral_task as child  # noqa: E402


class V24929UnicodeTotalNeutralGateTests(unittest.TestCase):
    def test_task_vector_is_fresh_neutral_and_label_blind(self) -> None:
        tasks = contract.task_vector()
        self.assertEqual(len(tasks), 20)
        self.assertEqual(len({task["opaque_id"] for task in tasks}), 20)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))
        self.assertTrue(all("Unicode" in task["question"] or "unicode" in task["question"] for task in tasks))

    def test_tasks_expose_nfkc_expansion_characters(self) -> None:
        questions = "\n".join(task["question"] for task in contract.task_vector())
        for glyph in ("½", "Ⅷ", "㎏", "℡", "™", "℃", "ﬃ", "㍑"):
            self.assertIn(glyph, questions)

    def test_production_capacity_and_caps(self) -> None:
        self.assertEqual(
            (contract.SELECTED_COUNT, contract.EXECUTOR_CONCURRENCY, contract.MODEL_SLOT_CAP),
            (20, 20, 8),
        )
        self.assertEqual(
            {name: contract.LIMITS[name] for name in (
                "wall_seconds", "model_calls", "search_queries", "fetch_targets"
            )},
            {"wall_seconds": 240, "model_calls": 3, "search_queries": 4, "fetch_targets": 10},
        )

    def test_keyless_gpt56_transport_is_inherited(self) -> None:
        self.assertEqual(contract.MODEL["proxy_url"], "http://127.0.0.1:9878/responses")
        self.assertEqual(contract.SEARCH["proxy_url"], contract.MODEL["proxy_url"])

    def test_projector_build_audit_is_valid(self) -> None:
        value = control._projector_audit()
        self.assertTrue(value["audit_valid"])
        self.assertEqual(POLICY_ID, "v24928_unicode_total_visible_row_sparse_table_compactor_v1")

    def test_all_four_watchers_are_protected(self) -> None:
        self.assertEqual(
            [item["pid"] for item in contract.protected_watcher_snapshot()],
            [795336, 3061652, 2808901, 2889939],
        )

    def test_runner_and_child_bind_neutral_namespace(self) -> None:
        runner.configure_algorithm()
        self.assertEqual(scheduler.OUTPUT_ROOT, contract.OUTPUT_ROOT)
        self.assertEqual(scheduler.SELECTED_COUNT, 20)
        self.assertEqual(scheduler.CHILD_MARKER, contract.CHILD_MARKER)
        child.configure()
        self.assertEqual(task_algorithm.OUTPUT_ROOT, contract.OUTPUT_ROOT)
        self.assertIs(
            child.runtime._evidence_projection,
            child.unicode_total_evidence_projection,
        )

    def test_synthetic_unicode_projection_receipt_is_valid(self) -> None:
        task = contract.task_vector()[0]
        child._VISIBLE_QUESTION = task["question"]
        try:
            limits = type("Limits", (), {"page_chars": 5000, "evidence_chars": 60000})()
            value = child.unicode_total_evidence_projection(
                [],
                [{
                    "results": [{
                        "title": "Neutral",
                        "url": "https://example.test/unicode",
                        "content": "Official compatibility examples: ½ Ⅷ ﬃ ①",
                    }]
                }],
                limits,
            )
            self.assertIsInstance(value, str)
            self.assertGreater(
                child._LAST_RECEIPT["compaction_receipt"]["nfkc_expansion_characters"],
                0,
            )
        finally:
            child._VISIBLE_QUESTION = None
            child._LAST_RECEIPT = None

    def test_runtime_semantic_audit_has_no_privileged_or_evaluator_capability(self) -> None:
        self.assertEqual(control._runtime_findings(), ([], [], []))

    def test_create_only_result_surface(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "result.json"
            runner._new_json(path, {})
            with self.assertRaises(FileExistsError):
                runner._new_json(path, {})


if __name__ == "__main__":
    unittest.main()
