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

from scripts import audit_v25120_grounded_target_record_build as target  # noqa: E402


class V25120GroundedTargetRecordBuildAuditTests(unittest.TestCase):
    def test_dependency_closure_contains_all_three_successors(self) -> None:
        closure = target._dependency_closure((target.RUNTIME_SOURCE,))
        self.assertIn(target.RUNTIME_SOURCE, closure)
        self.assertIn(target.PLAN_SOURCE, closure)
        self.assertIn(target.SELECTOR_SOURCE, closure)

    def test_direct_candidate_components_have_no_effect_imports(self) -> None:
        for source in (
            target.PLAN_SOURCE,
            target.SELECTOR_SOURCE,
            target.RUNTIME_SOURCE,
        ):
            with self.subTest(source=source):
                self.assertEqual(target._direct_forbidden_imports(source), [])

    def test_frozen_source_barrier_matches_pushed_implementation(self) -> None:
        self.assertEqual(target._source_barrier(), target.EXPECTED_SOURCE_HASHES)

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
            target, "_tracked", return_value=True
        ), mock.patch.object(target, "_tests", return_value=fake_tests), mock.patch.object(
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
                changed["authorization"]["evaluator_or_leaderboard_or_sota"] = True
            else:
                changed["tests"]["observed"] -= 1
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
