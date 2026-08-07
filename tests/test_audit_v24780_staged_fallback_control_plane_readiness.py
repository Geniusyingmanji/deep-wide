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

from scripts import audit_v24780_staged_fallback_control_plane_readiness as target  # noqa: E402


class V24780ControlPlaneReadinessTests(unittest.TestCase):
    def synthetic(self, *, parent=True, implementation=True, tests=True, lease=True,
                  runners=None, pristine=True, clean=True, pushed=True, label=False):
        suites = [
            {"path": str(path), "expected": count, "observed": count,
             "output_sha256": "a" * 64, "passed": True}
            for path, count in target.TEST_SUITES
        ]
        with (
            patch.object(target, "_manifest", return_value={"x": "b" * 64}),
            patch.object(target, "_parent_valid", return_value=parent),
            patch.object(target, "implementation_contract", return_value={"valid": implementation}),
            patch.object(target, "ast_findings", return_value=((['field'] if label else []), [], [], [])),
            patch.object(target, "_run_tests", return_value=(tests, target.EXPECTED_TESTS, suites)),
            patch.object(target, "_git", side_effect=["c" * 40, ("c" if pushed else "d") * 40, "" if clean else " M x"]),
            patch.object(target, "_tracked", return_value=True),
            patch.object(target.contract, "protected_watcher_snapshot", return_value=[]),
            patch.object(target, "_lease_inactive", return_value=lease),
            patch.object(target, "_active_runners", return_value=runners or []),
            patch.object(Path, "exists", return_value=not pristine),
            patch.object(Path, "is_symlink", return_value=False),
            patch.object(target, "_sha256", return_value="e" * 64),
        ):
            return target.build_audit(now=0)

    def test_actual_parent_ast_and_implementation_contract(self) -> None:
        self.assertTrue(target._parent_valid())
        self.assertEqual(target.ast_findings(), ([], [], [], []))
        self.assertTrue(target.implementation_contract()["valid"])

    def test_synthetic_go_authorizes_only_package_audit(self) -> None:
        value = self.synthetic()
        self.assertTrue(value["audit_valid"])
        self.assertTrue(value["authorization"]["package_audit_artifact_generation"])
        self.assertFalse(value["authorization"]["preactivation_audit_generation"])
        self.assertFalse(value["authorization"]["external_launch"])

    def test_parent_label_tests_or_state_failure_fails_closed(self) -> None:
        value = self.synthetic(parent=False, implementation=False, tests=False,
                               lease=False, runners=[1], pristine=False, label=True)
        for finding in (
            "protocol_parent_invalid", "implementation_contract_drifted",
            "privileged_forward_field_access", "regression_failed_or_count_drifted",
            "shared_api_lease_active", "v24780_runner_active", "future_surface_not_pristine",
        ):
            self.assertIn(finding, value["findings"])

    def test_expected_test_count_is_frozen(self) -> None:
        self.assertEqual(sum(count for _path, count in target.TEST_SUITES), 50)
        self.assertEqual(target.EXPECTED_TESTS, 50)

    def test_resealed_launch_tamper_is_rejected(self) -> None:
        value = self.synthetic()
        altered = copy.deepcopy(value)
        altered["authorization"]["external_launch"] = True
        altered.pop("audit_payload_sha256")
        altered["audit_payload_sha256"] = target.contract.payload_sha256(altered)
        with (
            patch.object(target, "_sha256", return_value="e" * 64),
            patch.object(target, "_manifest", return_value={"x": "b" * 64}),
        ):
            with self.assertRaises(RuntimeError):
                target.validate_audit(altered)


if __name__ == "__main__":
    unittest.main()
