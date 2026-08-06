from __future__ import annotations

import copy
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path: sys.path.insert(0, str(path))

from scripts import audit_v24665_external_package_build as audit  # noqa: E402


class V24665PackageAuditTests(unittest.TestCase):
    def synthetic(self, *, clean=True, parent=True, implementation=True, lease=False):
        tests = iter((True, count) for _path, count in audit.TEST_SUITES)
        with patch.object(audit, "_ordinary", side_effect=lambda path: ROOT / path), patch.object(
            audit, "_sha256", return_value="a" * 64
        ), patch.object(audit, "_forward_findings", return_value=([], [], [])), patch.object(
            audit, "_run_test", side_effect=lambda *_args: next(tests)
        ), patch.object(audit, "_git", side_effect=["c" * 40, "c" * 40, "" if clean else " M x"]), patch.object(
            audit, "_tracked", return_value=True
        ), patch.object(audit, "_parent_valid", return_value=parent), patch.object(
            audit, "_implementation_valid", return_value=implementation
        ), patch.object(audit, "lease_observation", return_value={"active": lease}), patch.object(
            audit, "protected_watcher_snapshot", return_value=[]
        ), patch.object(audit, "SECRET", re.compile(r"a^")):
            return audit.build_audit(now=0)

    def test_go_authorizes_protocol_only(self):
        value = self.synthetic(); audit.validate_audit(value)
        self.assertTrue(value["authorization"]["external_protocol_publication"])
        self.assertFalse(value["authorization"]["preactivation_audit"])
        self.assertFalse(value["authorization"]["activation_or_launch"])

    def test_parent_or_implementation_fails_closed(self):
        self.assertIn("v24663_population_parent_drifted", self.synthetic(parent=False)["findings"])
        self.assertIn("v24664_package_contract_drifted", self.synthetic(implementation=False)["findings"])

    def test_dirty_or_lease_fails_closed(self):
        self.assertIn("v24665_source_worktree_not_clean", self.synthetic(clean=False)["findings"])
        self.assertIn("shared_api_lease_active", self.synthetic(lease=True)["findings"])

    def test_test_count_frozen(self):
        self.assertEqual(sum(count for _path, count in audit.TEST_SUITES), 39)

    def test_resealed_launch_tamper_fails_closed(self):
        value = self.synthetic(); tampered = copy.deepcopy(value)
        tampered["authorization"]["activation_or_launch"] = True
        tampered.pop("audit_payload_sha256")
        tampered["audit_payload_sha256"] = audit.payload_sha256(tampered)
        with self.assertRaises(RuntimeError): audit.validate_audit(tampered)

    def test_forward_markers_exclude_private_evaluator_surfaces(self):
        markers, imports, secrets = audit._forward_findings()
        self.assertEqual(markers, []); self.assertEqual(imports, []); self.assertEqual(secrets, [])


if __name__ == "__main__": unittest.main()
