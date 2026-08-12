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

from scripts import audit_v25224_strict_cran_candidate_extractor_build as target  # noqa: E402


class V25224StrictCranCandidateExtractorBuildAuditTests(unittest.TestCase):
    @staticmethod
    def _fake_tests() -> dict[str, object]:
        return {
            "expected": target.EXPECTED_TESTS,
            "observed": target.EXPECTED_TESTS,
            "passed": True,
            "suites": [
                {
                    "pattern": pattern,
                    "expected": expected,
                    "observed": expected,
                    "returncode": 0,
                    "passed": True,
                    "output_sha256": "b" * 64,
                }
                for pattern, expected in target.TEST_SUITES
            ],
        }

    @staticmethod
    def _watchers() -> dict[str, dict[str, object]]:
        audit = target.base.base
        return {
            str(pid): {
                "present": True,
                "start_ticks": start,
                "matches_frozen_identity": True,
            }
            for pid, start in audit.PROTECTED_WATCHERS.items()
        }

    def test_fixed_hash_design_and_parent_barriers(self) -> None:
        self.assertTrue(target._hash_barrier())
        self.assertTrue(target._design_barrier())
        self.assertTrue(target._parent_barrier())

    def test_expected_suite_total_is_exact(self) -> None:
        self.assertEqual(target.EXPECTED_TESTS, 39)

    def test_dependency_closure_is_exactly_two_pure_label_blind_modules(self) -> None:
        closure = target.base.base._dependency_closure((target.EXTRACTOR_SOURCE,))
        self.assertEqual(closure, target.EXPECTED_CLOSURE)
        semantic = target.base.base._semantic_findings(closure)
        self.assertEqual(semantic["privileged_runtime_field_accesses"], [])
        self.assertEqual(semantic["evaluator_capabilities"], [])
        self.assertEqual(semantic["credential_literal_hits"], [])
        self.assertEqual(semantic["allowed_provider_rank_access"], [])

    def test_parent_predicate_and_attestation_constants_are_exact(self) -> None:
        self.assertIs(target.extractor.parent, target.parent)
        self.assertEqual(target.extractor.STRATUM, target.parent.STRATUM)
        self.assertEqual(
            target.extractor.FAILURE_STAGES,
            (*target.parent.FAILURE_STAGES, "candidate_count_parity"),
        )

    def test_dry_audit_is_valid_with_no_external_authority(self) -> None:
        audit = target.base.base
        fake_tests = self._fake_tests()

        def same(*args: str) -> str:
            return (
                "a" * 40
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
            return_value=self._watchers(),
        ), mock.patch.object(audit, "_lease_inactive", return_value=True):
            value = target.build_audit(now=1, tracked=False)
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["findings"], [])
        self.assertTrue(value["authorization"]["strict_cran_candidate_extractor_build_only"])
        self.assertFalse(value["authorization"]["fresh_semantic_transport_protocol_design"])
        self.assertFalse(value["authorization"]["public_snapshot_network_access_or_execution_start"])

    def test_resealed_authorization_hash_network_or_hidden_tamper_fails(self) -> None:
        audit = target.base.base
        fake_tests = self._fake_tests()

        def same(*args: str) -> str:
            return (
                "a" * 40
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
            return_value=self._watchers(),
        ), mock.patch.object(audit, "_lease_inactive", return_value=True):
            value = target.build_audit(now=1, tracked=False)
        for kind in ("authorization", "hash", "network", "alternate", "hidden"):
            changed = copy.deepcopy(value)
            if kind == "authorization":
                changed["authorization"]["fresh_semantic_transport_protocol_design"] = True
            elif kind == "hash":
                changed["fixed_artifact_hashes"][str(target.DESIGN)] = "0" * 64
            elif kind == "network":
                changed["network_model_search_fetch_evaluator_benchmark_or_api_called"] = True
            elif kind == "alternate":
                changed["known_safe_alternate_mime_allowlist_count"] = 1
            else:
                changed["hidden_identity"] = "private"
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)

        locations = (
            ("git",),
            ("tests",),
            ("tests", "suites", 0),
            ("semantic_audit",),
            ("runtime_state",),
            (
                "runtime_state",
                "protected_watchers",
                str(next(iter(audit.PROTECTED_WATCHERS))),
            ),
            ("checks",),
            ("authorization",),
        )
        for location in locations:
            changed = copy.deepcopy(value)
            container = changed
            for component in location:
                container = container[component]
            container["hidden_content"] = "must-not-survive-resealing"
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(location=location), self.assertRaises(ValueError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
