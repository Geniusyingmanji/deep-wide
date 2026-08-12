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

from scripts import audit_v25215_offline_candidate_discovery_build as target  # noqa: E402


class V25215OfflineCandidateDiscoveryBuildAuditTests(unittest.TestCase):
    def test_fixed_hash_and_r2_design_barriers(self) -> None:
        self.assertTrue(target._hash_barrier())
        self.assertTrue(target._design_barrier())

    def test_expected_suite_total_is_exact(self) -> None:
        self.assertEqual(target.EXPECTED_TESTS, 30)

    def test_dependency_closure_is_one_pure_module(self) -> None:
        closure = target.base.base._dependency_closure((target.DISCOVERY_SOURCE,))
        self.assertEqual(closure, (target.DISCOVERY_SOURCE,))
        self.assertEqual(
            target.base.base._direct_forbidden_imports(target.DISCOVERY_SOURCE), []
        )

    def test_semantic_capability_findings_are_zero(self) -> None:
        closure = target.base.base._dependency_closure((target.DISCOVERY_SOURCE,))
        semantic = target.base.base._semantic_findings(closure)
        self.assertEqual(semantic["privileged_runtime_field_accesses"], [])
        self.assertEqual(semantic["evaluator_capabilities"], [])
        self.assertEqual(semantic["credential_literal_hits"], [])
        self.assertEqual(semantic["allowed_provider_rank_access"], [])

    def test_r2_crates_predicate_is_not_old_unobservable_predicate(self) -> None:
        raw = __import__("json").loads(
            target.base.base._ordinary(target.DESIGN).read_text(encoding="utf-8")
        )
        self.assertEqual(
            raw["source_specs"]["single_authority_exact_record"][
                "selection_predicate"
            ],
            target.design.CORRECTED_CRATES_PREDICATE,
        )
        self.assertNotEqual(
            target.design.CORRECTED_CRATES_PREDICATE,
            "non_yanked_current_version_and_nonempty_description",
        )

    def test_resealed_authorization_hash_or_closure_tamper_fails(self) -> None:
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
        for kind in ("authorization", "hash", "closure"):
            changed = copy.deepcopy(value)
            if kind == "authorization":
                changed["authorization"]["public_index_snapshot_network_access"] = True
            elif kind == "hash":
                changed["fixed_artifact_hashes"][str(target.DESIGN)] = "0" * 64
            else:
                changed["dependency_closure"].append("src/deepwide_agent/clients.py")
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
