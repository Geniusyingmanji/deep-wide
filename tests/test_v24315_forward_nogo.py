from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24315_exact220_forward_nogo as audit  # noqa: E402
from scripts import publish_v24315_exact220_forward_nogo as target  # noqa: E402


class V24315ForwardNoGoTests(unittest.TestCase):
    @staticmethod
    def result_value() -> dict:
        if (ROOT / target.RESULT).is_file():
            value = target.read_object(ROOT / target.RESULT)
            target.validate_result(ROOT, value)
            return value
        return target.build_result(ROOT, now=1)

    def test_terminal_barrier_is_exact220_and_evaluator_absent(self) -> None:
        freeze, summary = target._validate_prediction_barrier(ROOT)
        self.assertEqual(freeze["terminal"], 220)
        self.assertEqual(summary["selected"], 220)
        self.assertFalse(freeze["mapping_gold_or_evaluator_opened_or_hashed"])
        self.assertFalse((ROOT / target.EVALUATOR_ROOT).exists())

    def test_disk_receipts_preserve_two_timeouts(self) -> None:
        value = target._disk_observability(ROOT)
        self.assertEqual(value["parent_receipts_valid"], 220)
        self.assertEqual(value["parent_taxonomy"], {"hard_deadline_timeout": 2, "success": 218})
        self.assertEqual(value["child_receipts_valid"], 218)
        self.assertEqual(value["model_receipts_valid"], 218)
        self.assertEqual(value["transport_receipts_valid"], 218)
        self.assertEqual(value["timeout_content_free_progress"]["stage_counts"], {"plan_terminal": 2})

    def test_result_is_strict_nogo_without_score_or_evaluator_authority(self) -> None:
        value = self.result_value()
        target.validate_result(ROOT, value)
        self.assertFalse(value["forward_gate"]["passed"])
        self.assertEqual(
            value["forward_gate"]["failed_checks"],
            [
                "incomplete_effect_counts",
                "non_success_parent_exits",
                "valid_child_terminal_receipts",
                "valid_model_slot_receipts",
                "valid_transport_receipts",
            ],
        )
        self.assertFalse(value["evaluation_authorized"])
        self.assertFalse(value["benchmark_score_available"])

    def test_publication_contains_no_task_ids_or_prediction_content(self) -> None:
        value = self.result_value()
        encoded = json.dumps(value, ensure_ascii=False)
        self.assertNotIn("task_0001", encoded)
        self.assertNotIn("task_0002", encoded)
        self.assertTrue(
            value["source_policy"][
                "question_opaque_id_prediction_url_page_or_credential_emitted_by_publication"
            ]
            is False
        )

    def test_closure_audit_is_valid_and_keeps_evaluator_closed(self) -> None:
        if not (ROOT / target.RESULT).exists():
            self.skipTest("NO-GO result is published after focused tests")
        value = audit.build_audit(ROOT, now=1)
        self.assertTrue(value["audit_valid"])
        self.assertTrue(value["closure"]["evaluator_side_surface_absent"])
        self.assertFalse(value["authorization"]["same_run_evaluator"])


if __name__ == "__main__":
    unittest.main()
