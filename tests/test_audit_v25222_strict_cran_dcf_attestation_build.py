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

from scripts import audit_v25222_strict_cran_dcf_attestation_build as target  # noqa: E402


class V25222StrictCranDcfAttestationBuildAuditTests(unittest.TestCase):
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
                "start_ticks": start_ticks,
                "matches_frozen_identity": True,
            }
            for pid, start_ticks in audit.PROTECTED_WATCHERS.items()
        }

    def test_fixed_hash_design_and_observer_barriers(self) -> None:
        self.assertTrue(target._hash_barrier())
        self.assertTrue(target._design_barrier())
        self.assertTrue(target._observer_barrier())

    def test_expected_suite_total_is_exact(self) -> None:
        self.assertEqual(target.EXPECTED_TESTS, 46)

    def test_dependency_closure_is_one_pure_label_blind_module(self) -> None:
        closure = target.base.base._dependency_closure((target.ATTESTOR_SOURCE,))
        self.assertEqual(closure, (target.ATTESTOR_SOURCE,))
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

    def test_attestor_threshold_and_failure_vocabulary_are_exact(self) -> None:
        self.assertEqual(target.attestor.MINIMUM_DISTINCT_CANDIDATES, 64)
        self.assertEqual(len(target.attestor.FAILURE_STAGES), 9)
        self.assertIn("body_sha256_binding", target.attestor.FAILURE_STAGES)
        self.assertIn("minimum_candidate_coverage", target.attestor.FAILURE_STAGES)

    def test_resealed_authorization_hash_or_network_tamper_fails(self) -> None:
        fake_tests = self._fake_tests()
        audit = target.base.base

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
        for kind in ("authorization", "hash", "network", "alternate"):
            changed = copy.deepcopy(value)
            if kind == "authorization":
                changed["authorization"]["fresh_transport_observability_protocol_design"] = True
            elif kind == "hash":
                changed["fixed_artifact_hashes"][str(target.DESIGN)] = "0" * 64
            elif kind == "network":
                changed["network_model_search_fetch_evaluator_benchmark_or_api_called"] = True
            else:
                changed["known_safe_alternate_mime_allowlist_count"] = 1
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)

    def test_resealed_top_level_and_nested_hidden_fields_fail(self) -> None:
        fake_tests = self._fake_tests()
        audit = target.base.base

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
        locations = (
            (),
            ("git",),
            ("tests",),
            ("tests", "suites", 0),
            ("direct_capability_audit",),
            ("semantic_audit",),
            ("runtime_state",),
            ("runtime_state", "protected_watchers", str(next(iter(audit.PROTECTED_WATCHERS)))),
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
