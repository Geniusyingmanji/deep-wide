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

from scripts import audit_v25231_header_totality_build as target  # noqa: E402


class V25231HeaderTotalityBuildAuditTests(unittest.TestCase):
    def test_fixed_sources_design_and_diagnosis_hashes_match(self) -> None:
        self.assertTrue(target._fixed_hash_barrier())
        self.assertEqual(
            target._fixed_hashes(),
            {str(path): expected for path, expected in target.FIXED_HASHES.items()},
        )

    def test_diagnosis_and_design_authority_is_exact(self) -> None:
        self.assertTrue(target._authority_barrier())

    def test_dependency_closure_is_exact_and_effect_free_at_entrypoint(self) -> None:
        closure = target.base._dependency_closure((target.IMPLEMENTATION,))
        self.assertEqual(closure, target.EXPECTED_CLOSURE)
        self.assertEqual(
            target.base._direct_forbidden_imports(target.IMPLEMENTATION), []
        )

    def test_semantic_audit_has_only_known_provider_rank_exception(self) -> None:
        semantic = target.base._semantic_findings(target.EXPECTED_CLOSURE)
        self.assertEqual(semantic["privileged_runtime_field_accesses"], [])
        self.assertEqual(semantic["evaluator_capabilities"], [])
        self.assertEqual(semantic["credential_literal_hits"], [])
        self.assertEqual(
            semantic["allowed_provider_rank_access"],
            ["src/deepwide_agent/clients.py:565:score"],
        )

    def test_expected_suite_and_vocabulary_totals_are_fixed(self) -> None:
        self.assertEqual(target.EXPECTED_TESTS, 59)
        self.assertEqual(len(target.normalizer.DISPOSITION_NAMES), 14)
        self.assertEqual(len(target.normalizer.COUNT_NAMES), 18)

    def test_resealed_authorization_test_or_closure_tamper_fails(self) -> None:
        fake_tests = {
            "expected": target.EXPECTED_TESTS,
            "observed": target.EXPECTED_TESTS,
            "passed": True,
            "suites": [],
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
            "allowed_provider_rank_access": [
                "src/deepwide_agent/clients.py:565:score"
            ],
        }
        with mock.patch.object(target.base, "_git", side_effect=same), mock.patch.object(
            target, "_tests", return_value=fake_tests
        ), mock.patch.object(
            target.base, "_dependency_closure", return_value=target.EXPECTED_CLOSURE
        ), mock.patch.object(
            target.base, "_semantic_findings", return_value=semantic
        ), mock.patch.object(
            target.base,
            "_watchers",
            return_value={
                str(pid): {"matches_frozen_identity": True}
                for pid in target.base.PROTECTED_WATCHERS
            },
        ), mock.patch.object(target.base, "_lease_inactive", return_value=True), mock.patch.object(
            target.base, "_tracked", return_value=True
        ):
            value = target.build_audit(now=1, tracked=False)
        for kind in ("authorization", "test", "closure"):
            changed = copy.deepcopy(value)
            if kind == "authorization":
                changed["authorization"]["fresh_external_activation_or_launch"] = True
            elif kind == "test":
                changed["tests"]["observed"] -= 1
            else:
                changed["runtime_dependency_closure"] = changed[
                    "runtime_dependency_closure"
                ][:-1]
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)

    def test_fully_mocked_clean_build_validates(self) -> None:
        fake_tests = {
            "expected": target.EXPECTED_TESTS,
            "observed": target.EXPECTED_TESTS,
            "passed": True,
            "suites": [],
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
            "allowed_provider_rank_access": [
                "src/deepwide_agent/clients.py:565:score"
            ],
        }
        with mock.patch.object(target.base, "_git", side_effect=same), mock.patch.object(
            target, "_tests", return_value=fake_tests
        ), mock.patch.object(
            target.base, "_dependency_closure", return_value=target.EXPECTED_CLOSURE
        ), mock.patch.object(
            target.base, "_semantic_findings", return_value=semantic
        ), mock.patch.object(
            target.base,
            "_watchers",
            return_value={
                str(pid): {"matches_frozen_identity": True}
                for pid in target.base.PROTECTED_WATCHERS
            },
        ), mock.patch.object(target.base, "_lease_inactive", return_value=True), mock.patch.object(
            target.base, "_tracked", return_value=True
        ):
            value = target.build_audit(now=1, tracked=False)
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["findings"], [])
        self.assertFalse(value["authorization"]["fresh_external_activation_or_launch"])


if __name__ == "__main__":
    unittest.main()
