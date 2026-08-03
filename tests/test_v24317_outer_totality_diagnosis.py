from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v24317_v24315_outer_totality as target  # noqa: E402
from scripts import audit_v24317_outer_totality_diagnosis as audit  # noqa: E402


class V24317OuterTotalityDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_report(ROOT, now=1)

    def test_exact_outer_failure_partition(self) -> None:
        self.assertEqual(self.value["positions"], list(target.EXPECTED_POSITIONS))
        self.assertEqual(
            self.value["mechanical_cause_counts"],
            {
                "deadline_deferred_cached_pages": 1,
                "logical_model_admission_rejected_before_provider": 17,
            },
        )

    def test_pre_provider_rejections_preserve_actual_request_accounting(self) -> None:
        rows = [row for row in self.value["rows"] if row["model_slot_timeouts"]]
        self.assertEqual(len(rows), 17)
        self.assertTrue(
            all(
                row["model_slot_acquisitions"] == row["terminal_model_requests"]
                and row["deadline_exhausted_at_receipt"]
                for row in rows
            )
        )

    def test_cache_deferral_is_unique_and_after_wall_budget(self) -> None:
        rows = [row for row in self.value["rows"] if not row["model_slot_timeouts"]]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["position"], 118)
        self.assertEqual(row["last_safe_stage"], "terminal")
        self.assertGreater(row["last_safe_elapsed_seconds"], 180)
        self.assertEqual(row["admitted_fetch_targets_at_last_safe_progress"], 0)
        self.assertGreater(
            row["search_fetch_calls_at_last_safe_progress"],
            row["search_fetch_failures_at_last_safe_progress"],
        )

    def test_publication_is_content_free_and_grants_no_launch(self) -> None:
        encoded = json.dumps(self.value, ensure_ascii=False).casefold()
        self.assertNotIn("task_0019", encoded)
        self.assertNotIn("prediction_sha256", encoded)
        self.assertFalse(self.value["authorization"]["benchmark_launch"])
        self.assertFalse(
            self.value["source_policy"][
                "same_run_mapping_gold_category_question_type_split_evaluator_score_read"
            ]
        )

    def test_closure_audit_has_no_findings(self) -> None:
        if os.environ.get("V24317_AUDIT_CHILD") == "1":
            self.skipTest("audit child does not recursively audit itself")
        if not (ROOT / target.RESULT).is_file():
            self.skipTest("diagnosis is published after initial focused tests")
        value = audit.build_audit(ROOT, now=1)
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["findings"], [])
        self.assertFalse(value["authorization"]["benchmark_launch"])


if __name__ == "__main__":
    unittest.main()
