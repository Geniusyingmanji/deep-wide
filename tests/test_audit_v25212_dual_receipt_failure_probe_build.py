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

from scripts import audit_v25212_dual_receipt_failure_probe_build as target  # noqa: E402


class V25212DualReceiptFailureProbeBuildAuditTests(unittest.TestCase):
    def test_fixed_hash_and_design_barriers(self) -> None:
        self.assertTrue(target._hash_barrier())
        self.assertTrue(target._design_barrier())

    def test_expected_suite_total_is_exact(self) -> None:
        self.assertEqual(target.EXPECTED_TESTS, 82)

    def test_import_time_install_is_absent(self) -> None:
        self.assertTrue(target._import_time_install_absent())

    def test_direct_probe_has_no_effect_imports(self) -> None:
        self.assertEqual(
            target.base.base._direct_forbidden_imports(target.PROBE_SOURCE), []
        )

    def test_probe_closure_is_label_blind_secret_free_and_evaluator_free(self) -> None:
        closure = target.base.base._dependency_closure((target.PROBE_SOURCE,))
        semantic = target.base.base._semantic_findings(closure)
        self.assertEqual(semantic["privileged_runtime_field_accesses"], [])
        self.assertEqual(semantic["evaluator_capabilities"], [])
        self.assertEqual(semantic["credential_literal_hits"], [])

    def test_resealed_authorization_hash_or_test_tamper_fails(self) -> None:
        fake_tests = {
            "expected": target.EXPECTED_TESTS,
            "observed": target.EXPECTED_TESTS,
            "passed": True,
            "suites": [],
        }
        audit = target.base.base

        def same(*args: str) -> str:
            return (
                "same"
                if args[:2] in {("rev-parse", "HEAD"), ("rev-parse", "target/main")}
                else ""
            )

        with mock.patch.object(audit, "_git", side_effect=same), mock.patch.object(
            target, "_tests", return_value=fake_tests
        ), mock.patch.object(
            audit,
            "_semantic_findings",
            return_value={
                "privileged_runtime_field_accesses": [],
                "evaluator_capabilities": [],
                "credential_literal_hits": [],
                "allowed_provider_rank_access": [],
            },
        ), mock.patch.object(
            audit,
            "_watchers",
            return_value={
                str(pid): {"matches_frozen_identity": True}
                for pid in audit.PROTECTED_WATCHERS
            },
        ), mock.patch.object(audit, "_lease_inactive", return_value=True):
            value = target.build_audit(now=1, tracked=False)
        for kind in ("authorization", "hash", "test"):
            changed = copy.deepcopy(value)
            if kind == "authorization":
                changed["authorization"]["probe_runtime_integration_or_external_activation"] = True
            elif kind == "hash":
                changed["fixed_artifact_hashes"][str(target.DESIGN)] = "0" * 64
            else:
                changed["tests"]["observed"] -= 1
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
