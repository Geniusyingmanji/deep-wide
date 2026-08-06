from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24698_v24694_activation_control_build as audit  # noqa: E402


class V24698ActivationControlAuditTests(unittest.TestCase):
    def synthetic(self, *, clean=True, lease=False, pristine=True):
        tests = iter((True, count) for _path, count, _timeout in audit.TEST_SUITES)
        with patch.object(audit, "sha256", return_value="a" * 64), patch.object(
            audit.control, "_forward_findings", return_value=([], [], [], [])
        ), patch.object(audit, "_run_test", side_effect=lambda *_args: next(tests)), patch.object(
            audit,
            "_git",
            side_effect=["c" * 40, "c" * 40, "" if clean else " M x"],
        ), patch.object(audit, "_tracked", return_value=True), patch.object(
            audit.control,
            "_validate_protocol",
            return_value={"task_contract": {"runtime_input_keys": ["opaque_id", "question"]}},
        ), patch.object(audit.control, "_validate_package", return_value={"audit_valid": True}), patch.object(
            audit, "protected_watcher_snapshot", return_value=[]
        ), patch.object(audit, "lease_observation", return_value={"active": lease}), patch.object(
            audit.Path, "exists", return_value=not pristine
        ), patch.object(audit.Path, "is_symlink", return_value=False):
            return audit.build_audit(now=0)

    def test_go_authorizes_preaudit_only(self) -> None:
        value = self.synthetic()
        audit.validate_audit(value)
        self.assertTrue(value["authorization"]["preactivation_audit_generation"])
        self.assertFalse(value["authorization"]["activation_or_launch"])
        self.assertFalse(value["authorization"]["evaluator"])

    def test_dirty_or_lease_fails_closed(self) -> None:
        self.assertIn("v24698_source_worktree_not_clean", self.synthetic(clean=False)["findings"])
        self.assertIn("shared_api_lease_active", self.synthetic(lease=True)["findings"])

    def test_future_surface_must_be_pristine(self) -> None:
        self.assertIn("v24694_future_surface_not_pristine", self.synthetic(pristine=False)["findings"])

    def test_test_count_is_frozen(self) -> None:
        self.assertEqual(sum(count for _path, count, _timeout in audit.TEST_SUITES), 35)

    def test_resealed_launch_tamper_fails_closed(self) -> None:
        value = self.synthetic()
        changed = copy.deepcopy(value)
        changed["authorization"]["activation_or_launch"] = True
        changed.pop("audit_payload_sha256")
        changed["audit_payload_sha256"] = audit.payload_sha256(changed)
        with self.assertRaises(RuntimeError):
            audit.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
