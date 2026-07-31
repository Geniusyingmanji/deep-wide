from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts.audit_v24212_failed_activation import build_audit  # noqa: E402


class AuditV24212FailedActivationTests(unittest.TestCase):
    def test_failed_activation_is_sealed_without_execution(self) -> None:
        value = build_audit(created_at_unix=1)
        self.assertEqual(
            value["failure"]["classification"],
            "successor_envelope_field_name_mismatch_fail_closed",
        )
        disposition = value["disposition"]
        self.assertTrue(disposition["original_watcher_process_absent"])
        self.assertTrue(disposition["original_activation_and_state_preserved"])
        self.assertTrue(disposition["new_versioned_recovery_protocol_required"])
        self.assertFalse(disposition["shared_api_lease_acquired"])
        self.assertFalse(disposition["benchmark_forward_or_full220_launch_allowed"])


if __name__ == "__main__":
    unittest.main()
