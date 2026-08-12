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

from scripts import audit_v25156_projection_structure_observer_build as target  # noqa: E402


class V25156ProjectionStructureObserverBuildAuditTests(unittest.TestCase):
    def test_dependency_closure_contains_observer_fetch_and_native_seam(self) -> None:
        closure = target.audit_parent._dependency_closure(
            (target.OBSERVER, target.FETCH, target.HELPER)
        )
        self.assertIn(target.OBSERVER, closure)
        self.assertIn(target.FETCH, closure)
        self.assertIn(target.HELPER, closure)
        self.assertIn(target.NATIVE, closure)

    def test_pure_observer_has_no_effect_imports(self) -> None:
        self.assertEqual(
            target.audit_parent._direct_forbidden_imports(target.OBSERVER), []
        )

    def test_expected_suite_total_is_exact(self) -> None:
        self.assertEqual(target.EXPECTED_TESTS, 63)

    def test_v25154_diagnosis_barrier(self) -> None:
        self.assertTrue(target._diagnosis_barrier())

    def test_old_v24981_source_has_no_worktree_diff(self) -> None:
        self.assertEqual(
            target.audit_parent._git(
                "diff", "--", "src/deepwide_agent/v24981_late_page_bound_fetch.py"
            ),
            "",
        )

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
                changed["authorization"]["fresh_external_activation_or_launch"] = True
            else:
                changed["tests"]["observed"] -= 1
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
