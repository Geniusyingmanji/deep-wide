from __future__ import annotations

import unittest
from unittest import mock

from scripts.audit_v24212_entropy_component_wait_activation import build_audit


class AuditV24212EntropyComponentWaitActivationTests(unittest.TestCase):
    def test_live_wait_audit_is_label_blind_and_nonlaunching(self) -> None:
        value = build_audit(created_at_unix=1)
        boundary = value["boundary"]
        self.assertTrue(boundary["selected_parent_report_and_model_unopened"])
        self.assertTrue(boundary["component_publication_absent"])
        self.assertTrue(boundary["projection_only_action_arm_forbidden"])
        self.assertFalse(boundary["shared_api_lease_acquired"])
        self.assertFalse(boundary["benchmark_forward_or_full220_launch_allowed"])

    def test_protected_process_drift_fails(self) -> None:
        with mock.patch(
            "scripts.audit_v24212_entropy_component_wait_activation.protected_processes",
            return_value={},
        ):
            with self.assertRaisesRegex(RuntimeError, "wait boundary"):
                build_audit(created_at_unix=1)


if __name__ == "__main__":
    unittest.main()
