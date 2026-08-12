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

from scripts import audit_v25181_quote_aware_runtime_build as target  # noqa: E402


class V25181QuoteAwareRuntimeBuildAuditTests(unittest.TestCase):
    def test_dependency_closure_contains_runtime_normalizer_and_parent_chain(self):
        closure = target.base._dependency_closure(
            (target.RUNTIME_SOURCE, target.NORMALIZER_SOURCE)
        )
        self.assertIn(target.RUNTIME_SOURCE, closure)
        self.assertIn(target.NORMALIZER_SOURCE, closure)
        self.assertIn(
            Path("src/deepwide_agent/v25165_observed_vertical_key_value_runtime.py"),
            closure,
        )
        self.assertFalse(any(path.parts[:1] == ("evaluation",) for path in closure))

    def test_direct_sources_have_no_effect_imports(self):
        self.assertEqual(
            target.base._direct_forbidden_imports(target.RUNTIME_SOURCE), []
        )
        self.assertEqual(
            target.base._direct_forbidden_imports(target.NORMALIZER_SOURCE), []
        )

    def test_parent_audit_loader_and_expected_suite_are_exact(self):
        self.assertEqual(target.EXPECTED_TESTS, 178)
        self.assertTrue(target._parent_barrier())
        nested = target.parent._nested_loader_receipt()
        self.assertEqual(nested["nested_head"], target.parent.EXPECTED_NESTED_HEAD)
        self.assertEqual(
            nested["blob_sha1"], target.parent.EXPECTED_PUBLIC_LOADER_BLOB
        )

    def _dry_run(self):
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
        ), mock.patch.object(
            target.base, "_lease_inactive", return_value=True
        ), mock.patch.object(
            target.parent,
            "_nested_loader_receipt",
            return_value={
                "nested_repository_relative_path": "external/Marco-Search-Agent",
                "nested_head": target.parent.EXPECTED_NESTED_HEAD,
                "file_relative_path": str(target.parent.NESTED_PUBLIC_LOADER),
                "tracked_in_nested_repository": True,
                "blob_sha1": target.parent.EXPECTED_PUBLIC_LOADER_BLOB,
                "working_file_sha256": target.parent.EXPECTED_PUBLIC_LOADER_SHA256,
                "working_file_matches_nested_head": True,
            },
        ):
            return target.build_audit(now=1, tracked=False)

    def test_clean_dry_run_authorizes_protocol_design_only(self):
        value = self._dry_run()
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["findings"], [])
        self.assertTrue(
            value["authorization"]["fresh_disjoint_external_protocol_design"]
        )
        self.assertFalse(
            value["authorization"]["fresh_external_activation_or_launch"]
        )

    def test_resealed_authority_test_credit_or_runtime_state_tamper_fails(self):
        value = self._dry_run()
        for kind in ("launch", "tests", "credit", "watcher", "lease"):
            changed = copy.deepcopy(value)
            if kind == "launch":
                changed["authorization"][
                    "fresh_external_activation_or_launch"
                ] = True
            elif kind == "tests":
                changed["tests"]["observed"] -= 1
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            elif kind == "watcher":
                first = next(iter(changed["runtime_state"]["protected_watchers"]))
                changed["runtime_state"]["protected_watchers"][first][
                    "matches_frozen_identity"
                ] = False
            else:
                changed["runtime_state"]["shared_api_lease_inactive"] = False
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
