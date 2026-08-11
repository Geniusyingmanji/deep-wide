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

from scripts import audit_v25128_causally_coupled_target_record_build as target  # noqa: E402


class V25128CausallyCoupledTargetRecordBuildAuditTests(unittest.TestCase):
    def test_dependency_closure_contains_successor_and_grounded_parent(self) -> None:
        closure = target._dependency_closure((target.RUNTIME_SOURCE,))
        self.assertIn(target.RUNTIME_SOURCE, closure)
        self.assertIn(
            Path("src/deepwide_agent/v25123_visible_legacy_query_compatible_runtime.py"),
            closure,
        )

    def test_direct_candidate_has_no_effect_imports(self) -> None:
        self.assertEqual(target._direct_forbidden_imports(target.RUNTIME_SOURCE), [])

    def test_parent_no_go_diagnosis_barrier(self) -> None:
        self.assertTrue(target._diagnosis_barrier())

    def test_resealed_authorization_or_test_count_tamper_fails(self) -> None:
        fake_tests = {
            "expected": target.EXPECTED_TESTS,
            "observed": target.EXPECTED_TESTS,
            "passed": True,
            "suites": [],
        }

        def same(*args: str) -> str:
            return "same" if args[:2] in {
                ("rev-parse", "HEAD"),
                ("rev-parse", "target/main"),
            } else ""

        with mock.patch.object(target, "_git", side_effect=same), mock.patch.object(
            target, "_tests", return_value=fake_tests
        ), mock.patch.object(
            target,
            "_semantic_findings",
            return_value={
                "privileged_runtime_field_accesses": [],
                "evaluator_capabilities": [],
                "credential_literal_hits": [],
                "allowed_provider_rank_access": [],
            },
        ), mock.patch.object(
            target,
            "_watchers",
            return_value={
                str(pid): {"matches_frozen_identity": True}
                for pid in target.PROTECTED_WATCHERS
            },
        ), mock.patch.object(target, "_lease_inactive", return_value=True):
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
