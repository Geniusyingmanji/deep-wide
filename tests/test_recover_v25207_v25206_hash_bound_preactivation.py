from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import recover_v25207_v25206_hash_bound_preactivation as target  # noqa: E402


class V25207HashBoundPreactivationRecoveryTests(unittest.TestCase):
    def test_frozen_full_test_proof_is_exact_and_manifest_bound(self) -> None:
        build, protocol, manifest = target._frozen_parents(tracked=True)
        self.assertEqual(build["tests"]["expected"], 324)
        self.assertEqual(build["tests"]["observed"], 324)
        self.assertTrue(build["tests"]["passed"])
        self.assertEqual(build["source_manifest"], manifest)
        self.assertEqual(protocol["source_manifest"], manifest)

    def test_recovery_implementation_is_label_blind_network_free(self) -> None:
        value = target._implementation_audit(tracked=False)
        self.assertTrue(value["audit_valid"], value["findings"])
        self.assertEqual(value["privileged_accesses"], [])
        self.assertEqual(value["test_count"], 5)

    def test_recovery_audit_withholds_forward_and_evaluator_authority(self) -> None:
        with mock.patch.object(
            target, "_run_recovery_tests", return_value={
                "expected": 5,
                "observed": 5,
                "returncode": 0,
                "passed": True,
                "output_sha256": "0" * 64,
            }
        ), mock.patch.object(target.control, "_future_pristine", return_value=True), mock.patch.object(
            target.control, "_endpoint_reachable", return_value=True
        ), mock.patch.object(target.control, "_lease_inactive", return_value=True), mock.patch.object(
            target.control, "_active_conflicts", return_value=[]
        ):
            value = target.build_recovery_audit(
                now=1, require_clean=False, tracked=False
            )
        self.assertTrue(value["audit_valid"], value["findings"])
        self.assertFalse(value["authorization"]["external_forward"])
        self.assertFalse(value["authorization"]["external_evaluator"])

    def test_live_manifest_drift_invalidates_frozen_proof(self) -> None:
        original = target.contract.dependency_manifest

        def drift(root: Path, *, tracked: bool) -> dict[str, str]:
            value = dict(original(root, tracked=tracked))
            value["synthetic_drift.py"] = "0" * 64
            return value

        with mock.patch.object(target.contract, "dependency_manifest", side_effect=drift):
            with self.assertRaises(RuntimeError):
                target._frozen_parents(tracked=True)

    def test_recovered_preaudit_tamper_fails_closed(self) -> None:
        recovery = {
            "audit_valid": True,
        }
        original_sha256 = target.contract.sha256

        def recovery_sha256(path: Path) -> str:
            if Path(path) == ROOT / target.RECOVERY_AUDIT:
                return "a" * 64
            return original_sha256(path)

        with mock.patch.object(
            target, "validate_recovery_audit", return_value=recovery
        ), mock.patch.object(target, "_read", return_value=recovery), mock.patch.object(
            target.control, "_clean_pushed", return_value=("head", "head")
        ), mock.patch.object(target.control, "_semantic_audit", return_value={
            "privileged_runtime_field_accesses": [],
            "evaluator_capabilities": [],
            "credential_literal_hits": [],
        }), mock.patch.object(target.control, "_selection_valid", return_value=True), mock.patch.object(
            target.control, "_diagnosis_valid", return_value=True
        ), mock.patch.object(target.control, "_future_pristine", return_value=True), mock.patch.object(
            target.control, "_endpoint_reachable", return_value=True
        ), mock.patch.object(target.control, "_lease_inactive", return_value=True), mock.patch.object(
            target.control, "_active_conflicts", return_value=[]
        ), mock.patch.object(target.contract, "sha256", side_effect=recovery_sha256), mock.patch.object(
            target, "validate_recovered_preaudit", side_effect=lambda value: value
        ):
            value = target.build_recovered_preaudit(now=1)
        changed = copy.deepcopy(value)
        changed["test_proof"]["no_test_scope_reduction"] = False
        with mock.patch.object(
            target.contract, "sha256", side_effect=recovery_sha256
        ), self.assertRaises(RuntimeError):
            target.validate_recovered_preaudit(changed)


if __name__ == "__main__":
    unittest.main()
