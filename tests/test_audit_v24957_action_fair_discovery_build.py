from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24957_action_fair_discovery_build as audit  # noqa: E402


class V24957ActionFairBuildAuditTests(unittest.TestCase):
    def test_synthetic_proves_set_conservation_and_prefix_gain(self) -> None:
        value = audit._synthetic()
        self.assertTrue(value["source_set_equal"])
        self.assertTrue(value["query_local_prefix_preserved"])
        self.assertGreater(value["action_group_coverage_gain"], 0)
        self.assertFalse(value["content_values_persisted"])

    def test_build_fails_closed_and_authorizes_no_benchmark(self) -> None:
        with patch.object(
            audit,
            "_tests",
            return_value={
                "modules": list(audit.TEST_MODULES),
                "expected": audit.EXPECTED_TESTS,
                "observed_passes": audit.EXPECTED_TESTS,
                "returncode": 0,
                "passed": True,
            },
        ):
            value = audit.build(now=1, require_clean=False)
        self.assertTrue(value["audit_valid"])
        self.assertTrue(value["authorization"]["neutral_live_transport_gate_design"])
        self.assertFalse(value["authorization"]["neutral_live_transport_gate_launch"])
        self.assertFalse(value["authorization"]["benchmark_external_or_exact220_launch"])
        self.assertFalse(value["authorization"]["evaluator"])


if __name__ == "__main__":
    unittest.main()
