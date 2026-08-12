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

from scripts import audit_v25220_content_type_disposition_build as target  # noqa: E402


class V25220ContentTypeDispositionBuildAuditTests(unittest.TestCase):
    def test_fixed_hash_parent_and_no_go_barriers(self) -> None:
        self.assertTrue(target._hash_barrier())
        self.assertTrue(target._parent_barrier())
        self.assertTrue(target._no_go_barrier())

    def test_expected_suite_total_is_exact(self) -> None:
        self.assertEqual(target.EXPECTED_TESTS, 42)

    def test_dependency_closure_is_one_pure_label_blind_module(self) -> None:
        closure = target.base.base._dependency_closure((target.OBSERVER_SOURCE,))
        self.assertEqual(closure, (target.OBSERVER_SOURCE,))
        semantic = target.base.base._semantic_findings(closure)
        self.assertEqual(semantic["privileged_runtime_field_accesses"], [])
        self.assertEqual(semantic["evaluator_capabilities"], [])
        self.assertEqual(semantic["credential_literal_hits"], [])

    def test_direct_effect_capability_is_absent(self) -> None:
        value = target._direct_capability()
        self.assertEqual(
            value[
                "filesystem_process_environment_network_model_search_evaluator_imports"
            ],
            [],
        )
        self.assertEqual(value["top_level_effect_calls"], [])

    def test_empty_alternate_allowlist_and_parent_acceptance_are_exact(self) -> None:
        self.assertEqual(
            target.observer.KNOWN_SAFE_ALTERNATES,
            {stratum: () for stratum in target.observer.STRATA},
        )
        self.assertEqual(
            target.observer.ACCEPTED_CONTENT_TYPES[
                "single_authority_multivalue_record"
            ],
            ("text/plain",),
        )

    def test_resealed_authorization_hash_or_alternate_count_tamper_fails(self) -> None:
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
        for kind in ("authorization", "hash", "alternate", "network"):
            changed = copy.deepcopy(value)
            if kind == "authorization":
                changed["authorization"]["known_safe_alternate_allowlist_change"] = True
            elif kind == "hash":
                changed["fixed_artifact_hashes"][str(target.NO_GO_RESULT)] = "0" * 64
            elif kind == "alternate":
                changed["known_safe_alternate_allowlist_count"] = 1
            else:
                changed["network_model_search_fetch_evaluator_benchmark_or_api_called"] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
