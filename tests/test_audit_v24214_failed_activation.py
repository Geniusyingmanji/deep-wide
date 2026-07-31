from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from scripts.audit_v24214_failed_activation import build_audit


ROOT = Path(__file__).resolve().parents[1]


class AuditV24214FailedActivationTests(unittest.TestCase):
    def test_failure_audit_seals_path_mismatch_without_benchmark_authority(self) -> None:
        with mock.patch(
            "scripts.audit_v24214_failed_activation.protected_processes",
            return_value={"r1": {"pid": 1}},
        ):
            value = build_audit(ROOT, created_at_unix=1)
        failure = value["failure"]
        self.assertEqual(
            failure["classification"],
            "entropy_publication_path_binding_mismatch_fail_closed",
        )
        self.assertFalse(failure["paths_equal"])
        self.assertTrue(failure["detected_before_parent_terminal_or_selected_content_open"])
        self.assertFalse(value["boundary"]["component_publications_opened"])
        self.assertFalse(value["boundary"]["joint_candidate_or_publication_created"])
        self.assertFalse(value["boundary"]["package_gate_evaluated_or_launched"])
        self.assertFalse(value["boundary"]["dev64_launched"])
        self.assertFalse(value["boundary"]["benchmark_forward_or_full220_launched"])
        self.assertFalse(
            value["disposition"]["same_namespace_restart_retry_resume_or_overwrite_allowed"]
        )
        self.assertTrue(value["disposition"]["new_versioned_recovery_protocol_required"])


if __name__ == "__main__":
    unittest.main()
