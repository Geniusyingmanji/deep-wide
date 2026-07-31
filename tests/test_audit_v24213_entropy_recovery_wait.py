from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts.audit_v24213_entropy_recovery_wait import build_audit  # noqa: E402


class AuditV24213EntropyRecoveryWaitTests(unittest.TestCase):
    def test_live_recovery_wait_is_nonlaunching(self) -> None:
        value = build_audit(created_at_unix=1)
        boundary = value["boundary"]
        self.assertTrue(boundary["recovery_delta_exactly_upstream_false_field_name"])
        self.assertTrue(boundary["failed_v24212_activation_and_state_preserved"])
        self.assertTrue(boundary["selected_parent_report_and_model_unopened"])
        self.assertFalse(boundary["shared_api_lease_acquired"])
        self.assertFalse(boundary["benchmark_forward_or_full220_launch_allowed"])


if __name__ == "__main__":
    unittest.main()
