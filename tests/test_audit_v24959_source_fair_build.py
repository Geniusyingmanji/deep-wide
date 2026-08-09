from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24959_source_fair_build as audit  # noqa: E402


class V24959SourceFairBuildAuditTests(unittest.TestCase):
    def test_synthetic_proves_every_prefix_non_decreasing(self) -> None:
        value = audit._synthetic()
        self.assertTrue(value["source_set_equal"])
        self.assertTrue(value["all_prefix_source_coverage_non_decreasing"])
        self.assertGreater(value["maximum_prefix_source_coverage_gain"], 0)
        self.assertTrue(value["cap6_matched_cost"])

    def test_build_authorizes_no_live_or_benchmark_launch(self) -> None:
        with patch.object(audit, "_tests", return_value={
            "modules": list(audit.TEST_MODULES), "expected": audit.EXPECTED_TESTS,
            "observed_passes": audit.EXPECTED_TESTS, "returncode": 0, "passed": True,
        }):
            value = audit.build(now=1, require_clean=False)
        self.assertTrue(value["audit_valid"])
        self.assertTrue(value["authorization"]["neutral_source_fair_live_gate_design"])
        self.assertFalse(value["authorization"]["neutral_source_fair_live_gate_launch"])
        self.assertFalse(value["authorization"]["benchmark_external_or_exact220_launch"])
        self.assertFalse(value["authorization"]["evaluator"])


if __name__ == "__main__":
    unittest.main()
