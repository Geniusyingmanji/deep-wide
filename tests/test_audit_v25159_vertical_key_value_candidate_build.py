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

from scripts import (  # noqa: E402
    audit_v25159_vertical_key_value_candidate_build as target,
)


class V25159VerticalBinderBuildAuditTests(unittest.TestCase):
    def test_dependency_closure_contains_successor_parent_and_verifier(self) -> None:
        closure = target.audit_parent._dependency_closure((target.RUNTIME_SOURCE,))
        self.assertIn(target.RUNTIME_SOURCE, closure)
        self.assertIn(
            Path("src/deepwide_agent/v25151_generic_record_quote_candidate_runtime.py"),
            closure,
        )
        self.assertIn(
            Path("src/deepwide_agent/v25143_quote_attested_cell_edit_runtime.py"),
            closure,
        )

    def test_direct_candidate_has_no_effect_imports(self) -> None:
        self.assertEqual(
            target.audit_parent._direct_forbidden_imports(target.RUNTIME_SOURCE),
            [],
        )

    def test_expected_suite_total_is_exact(self) -> None:
        self.assertEqual(target.EXPECTED_TESTS, 159)

    def test_v25157_no_go_parent_barrier(self) -> None:
        self.assertTrue(target._parent_barrier())

    def test_resealed_authorization_or_test_count_tamper_fails(self) -> None:
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
                in {
                    ("rev-parse", "HEAD"),
                    ("rev-parse", "target/main"),
                }
                else ""
            )

        with mock.patch.object(
            target.audit_parent, "_git", side_effect=same
        ), mock.patch.object(
            target, "_tests", return_value=fake_tests
        ), mock.patch.object(
            target.audit_parent,
            "_semantic_findings",
            return_value={
                "privileged_runtime_field_accesses": [],
                "evaluator_capabilities": [],
                "credential_literal_hits": [],
                "allowed_provider_rank_access": [],
            },
        ), mock.patch.object(
            target.audit_parent,
            "_watchers",
            return_value={
                str(pid): {"matches_frozen_identity": True}
                for pid in target.audit_parent.PROTECTED_WATCHERS
            },
        ), mock.patch.object(
            target.audit_parent, "_lease_inactive", return_value=True
        ):
            value = target.build_audit(now=1, tracked=False)
        for kind in ("authorization", "count"):
            changed = copy.deepcopy(value)
            if kind == "authorization":
                changed["authorization"][
                    "fresh_disjoint_external_protocol_design"
                ] = True
            else:
                changed["tests"]["observed"] -= 1
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
