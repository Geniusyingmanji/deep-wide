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

from scripts import audit_v25210_receipt_disposition_observer_build as target  # noqa: E402


class V25210ReceiptDispositionObserverBuildAuditTests(unittest.TestCase):
    def test_observer_dependency_closure_is_exactly_one_pure_module(self) -> None:
        closure = target.base._dependency_closure((target.OBSERVER_SOURCE,))
        self.assertEqual(closure, (target.OBSERVER_SOURCE,))
        self.assertEqual(
            target.base._direct_forbidden_imports(target.OBSERVER_SOURCE), []
        )

    def test_fixed_parent_source_and_stage_hashes_match(self) -> None:
        self.assertTrue(target._fixed_hash_barrier())
        self.assertEqual(target._fixed_hashes(), {
            str(path): expected for path, expected in target.FIXED_HASHES.items()
        })

    def test_v25209_reliability_diagnosis_is_exactly_bound(self) -> None:
        self.assertTrue(target._diagnosis_barrier())

    def test_expected_strict_suite_total_and_vocabularies_are_exact(self) -> None:
        self.assertEqual(target.EXPECTED_TESTS, 104)
        self.assertEqual(len(target.observer.SPARSE_VIOLATION_CODES), 35)
        self.assertEqual(len(target.observer.QUOTE_VIOLATION_CODES), 29)

    def test_v25206_historical_stage_evidence_is_hash_bound(self) -> None:
        self.assertTrue(target._historical_stage_evidence())

    def test_resealed_authorization_hash_or_stage_tamper_fails(self) -> None:
        fake_tests = {
            "expected": target.EXPECTED_TESTS,
            "observed": target.EXPECTED_TESTS,
            "passed": True,
            "suites": [],
        }
        fake_historical = {
            "pattern": target.HISTORICAL_PATTERN,
            "expected": 7,
            "observed": 7,
            "passed_tests": 6,
            "expected_stage_sensitive_failures": 1,
            "suite_returncode": 1,
            "classification": "historical_absence_assertion_after_authorized_evaluator_materialization",
            "classified_expected": True,
            "observer_regression": False,
            "output_sha256": "0" * 64,
        }

        def same(*args: str) -> str:
            return (
                "same"
                if args[:2] in {("rev-parse", "HEAD"), ("rev-parse", "target/main")}
                else ""
            )

        semantic = {
            "privileged_runtime_field_accesses": [],
            "evaluator_capabilities": [],
            "credential_literal_hits": [],
            "allowed_provider_rank_access": [],
        }
        with mock.patch.object(target.base, "_git", side_effect=same), mock.patch.object(
            target, "_tests", return_value=fake_tests
        ), mock.patch.object(
            target, "_historical_stage_test", return_value=fake_historical
        ), mock.patch.object(
            target, "_historical_stage_evidence", return_value=True
        ), mock.patch.object(
            target.base, "_semantic_findings", return_value=semantic
        ), mock.patch.object(
            target.base,
            "_watchers",
            return_value={
                str(pid): {"matches_frozen_identity": True}
                for pid in target.base.PROTECTED_WATCHERS
            },
        ), mock.patch.object(target.base, "_lease_inactive", return_value=True):
            value = target.build_audit(now=1, tracked=False)

        for kind in ("authorization", "hash", "stage"):
            changed = copy.deepcopy(value)
            if kind == "authorization":
                changed["authorization"]["fresh_external_activation_or_launch"] = True
            elif kind == "hash":
                changed["fixed_artifact_hashes"][str(target.DIAGNOSIS)] = "f" * 64
            else:
                changed["historical_stage_sensitive_parent_suite"][
                    "observer_regression"
                ] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
