from __future__ import annotations

import copy
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24660_support_closure_build as audit  # noqa: E402


class V24660BuildAuditTests(unittest.TestCase):
    def synthetic(self, *, clean=True, parent=True, implementation=True, lease=False):
        tests = iter((True, count) for _path, count in audit.TEST_SUITES)
        watchers = [
            {"pid": 795336, "marker": "a", "start_ticks": 1},
            {"pid": 3061652, "marker": "b", "start_ticks": 2},
        ]
        with patch.object(audit, "_ordinary", side_effect=lambda path: ROOT / path), patch.object(
            audit, "_sha256", return_value="a" * 64
        ), patch.object(audit, "_ast_findings", return_value=([], [])), patch.object(
            audit, "_run_test", side_effect=lambda *_args: next(tests)
        ), patch.object(
            audit, "_git", side_effect=["c" * 40, "c" * 40, "" if clean else " M plan.md"]
        ), patch.object(audit, "_tracked", return_value=True), patch.object(
            audit, "_parent_valid", return_value=parent
        ), patch.object(audit, "_implementation_valid", return_value=implementation), patch.object(
            audit, "lease_observation", return_value={"active": lease}
        ), patch.object(audit, "protected_watcher_snapshot", return_value=watchers), patch.object(
            audit, "SECRET", re.compile(r"a^")
        ):
            return audit.build_audit(now=0)

    def test_synthetic_go_authorizes_external_design_only(self):
        value = self.synthetic()
        audit.validate_audit(value)
        self.assertTrue(value["authorization"]["fresh_external_design"])
        self.assertFalse(value["authorization"]["fresh_external_launch"])
        self.assertFalse(value["authorization"]["paired_dev64_design"])
        self.assertFalse(value["authorization"]["exact220"])

    def test_parent_or_implementation_drift_fails_closed(self):
        parent = self.synthetic(parent=False)
        implementation = self.synthetic(implementation=False)
        self.assertIn("v24657_no_go_parent_drifted", parent["findings"])
        self.assertIn("v24659_support_closure_contract_drifted", implementation["findings"])

    def test_dirty_or_active_lease_fails_closed(self):
        dirty = self.synthetic(clean=False)
        lease = self.synthetic(lease=True)
        self.assertIn("v24660_source_worktree_not_clean", dirty["findings"])
        self.assertIn("shared_api_lease_active", lease["findings"])

    def test_test_count_is_frozen(self):
        self.assertEqual(sum(count for _path, count in audit.TEST_SUITES), 21)
        self.assertEqual(audit.EXPECTED_TEST_COUNT, 21)

    def test_resealed_launch_tamper_fails_closed(self):
        value = self.synthetic()
        tampered = copy.deepcopy(value)
        tampered["authorization"]["fresh_external_launch"] = True
        tampered.pop("audit_payload_sha256")
        tampered["audit_payload_sha256"] = audit.payload_sha256(tampered)
        with self.assertRaises(RuntimeError):
            audit.validate_audit(tampered)

    def test_mechanism_keeps_support_threshold_and_zero_entropy_credit(self):
        value = self.synthetic()["mechanism"]
        self.assertEqual(value["minimum_independent_support_sources"], 2)
        self.assertFalse(value["support_threshold_relaxed"])
        self.assertFalse(value["proposal_value_changed_by_closure"])
        self.assertFalse(value["new_search_fetch_or_model_effect"])
        self.assertFalse(value["entropy_or_task_credit_used"])


if __name__ == "__main__":
    unittest.main()
