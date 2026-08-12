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

from scripts import audit_v25178_quote_aware_normalizer_build as target  # noqa: E402


class V25178QuoteAwareNormalizerBuildAuditTests(unittest.TestCase):
    def test_dependency_closure_contains_only_public_pure_dependencies(self) -> None:
        closure = target.base._dependency_closure((target.NORMALIZER_SOURCE,))
        self.assertIn(target.NORMALIZER_SOURCE, closure)
        self.assertIn(
            Path("src/deepwide_agent/v24257_score_first_runtime.py"), closure
        )
        self.assertFalse(any(path.parts[:1] == ("evaluation",) for path in closure))

    def test_direct_source_has_no_network_or_evaluator_import(self) -> None:
        self.assertEqual(
            target.base._direct_forbidden_imports(target.NORMALIZER_SOURCE), []
        )

    def test_expected_suite_total_and_parent_barrier_are_exact(self) -> None:
        self.assertEqual(target.EXPECTED_TESTS, 36)
        self.assertTrue(target._parent_barrier())

    def test_clean_dry_run_authorizes_integration_design_only(self) -> None:
        fake_tests = {
            "expected": target.EXPECTED_TESTS,
            "observed": target.EXPECTED_TESTS,
            "passed": True,
            "suites": [],
        }

        def same(*args: str) -> str:
            return (
                "same"
                if args[:2]
                in {("rev-parse", "HEAD"), ("rev-parse", "target/main")}
                else ""
            )

        with mock.patch.object(
            target.base, "_git", side_effect=same
        ), mock.patch.object(
            target, "_tests", return_value=fake_tests
        ), mock.patch.object(
            target.base,
            "_semantic_findings",
            return_value={
                "privileged_runtime_field_accesses": [],
                "evaluator_capabilities": [],
                "credential_literal_hits": [],
                "allowed_provider_rank_access": [],
            },
        ), mock.patch.object(
            target.base,
            "_watchers",
            return_value={
                str(pid): {"matches_frozen_identity": True}
                for pid in target.base.PROTECTED_WATCHERS
            },
        ), mock.patch.object(target.base, "_lease_inactive", return_value=True):
            value = target.build_audit(now=1, tracked=False)
        self.assertTrue(value["audit_valid"])
        self.assertTrue(value["authorization"]["runtime_integration_design"])
        self.assertFalse(
            value["authorization"]["runtime_integration_implementation"]
        )
        self.assertFalse(value["authorization"]["fresh_external_protocol_or_launch"])

    def test_resealed_authority_count_or_credit_tamper_fails(self) -> None:
        fake_tests = {
            "expected": target.EXPECTED_TESTS,
            "observed": target.EXPECTED_TESTS,
            "passed": True,
            "suites": [],
        }
        with mock.patch.object(
            target.base,
            "_git",
            side_effect=lambda *args: "same"
            if args[:2]
            in {("rev-parse", "HEAD"), ("rev-parse", "target/main")}
            else "",
        ), mock.patch.object(
            target, "_tests", return_value=fake_tests
        ), mock.patch.object(
            target.base,
            "_semantic_findings",
            return_value={
                "privileged_runtime_field_accesses": [],
                "evaluator_capabilities": [],
                "credential_literal_hits": [],
                "allowed_provider_rank_access": [],
            },
        ), mock.patch.object(
            target.base,
            "_watchers",
            return_value={
                str(pid): {"matches_frozen_identity": True}
                for pid in target.base.PROTECTED_WATCHERS
            },
        ), mock.patch.object(target.base, "_lease_inactive", return_value=True):
            value = target.build_audit(now=1, tracked=False)
        for kind in ("implementation", "external", "count", "credit"):
            changed = copy.deepcopy(value)
            if kind == "implementation":
                changed["authorization"]["runtime_integration_implementation"] = True
            elif kind == "external":
                changed["authorization"]["fresh_external_protocol_or_launch"] = True
            elif kind == "count":
                changed["tests"]["observed"] -= 1
            else:
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
