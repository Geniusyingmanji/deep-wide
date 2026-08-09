from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v24961_v24960_failure as diagnosis  # noqa: E402


class V24961V24960FailureDiagnosisTests(unittest.TestCase):
    def test_synthetic_reproduces_local_failure_and_cumulative_success(self) -> None:
        value = diagnosis.synthetic_reproduction()
        self.assertTrue(value["legacy_local_invariant_raises"])
        self.assertTrue(value["repaired_cumulative_invariant_accepts"])
        self.assertLess(value["candidate_current_sources"], value["control_current_sources"])
        self.assertGreaterEqual(value["candidate_cumulative_sources"], value["control_cumulative_sources"])

    def test_parent_diagnosis_uses_aggregate_only_and_authorizes_no_rerun(self) -> None:
        value = diagnosis.build(now=1)
        self.assertTrue(value["diagnosis_valid"])
        self.assertTrue(value["source_policy"]["parent_aggregate_only"])
        self.assertFalse(value["source_policy"]["parent_task_query_url_page_prediction_or_evaluator_opened"])
        self.assertFalse(value["authorization"]["same_population_retry_resume_or_rerun"])
        self.assertFalse(value["authorization"]["benchmark_external_or_exact220_launch"])


if __name__ == "__main__":
    unittest.main()
