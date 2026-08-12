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

from scripts import audit_v25226_cran_semantic_transport_build as target  # noqa: E402


class V25226CranSemanticTransportBuildAuditTests(unittest.TestCase):
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

    def test_expected_suite_total_and_dependency_closure_are_exact(self) -> None:
        self.assertEqual(target.EXPECTED_TESTS, 48)
        closure = target.base.base._dependency_closure((target.RUNTIME_SOURCE,))
        self.assertEqual(closure, target.EXPECTED_CLOSURE)

    def test_network_capability_is_inherited_only_from_frozen_v25217(self) -> None:
        capability = target._direct_capability()
        self.assertEqual(capability["direct_forbidden_imports"], [])
        self.assertEqual(
            capability["closure_forbidden_imports"],
            {str(target.TRANSPORT_SOURCE): ["requests", "socket"]},
        )

    def test_semantic_findings_are_zero(self) -> None:
        semantic = target.base.base._semantic_findings(target.EXPECTED_CLOSURE)
        self.assertEqual(semantic["privileged_runtime_field_accesses"], [])
        self.assertEqual(semantic["evaluator_capabilities"], [])
        self.assertEqual(semantic["credential_literal_hits"], [])
        self.assertEqual(semantic["allowed_provider_rank_access"], [])

    def _dry_value(self) -> dict[str, object]:
        audit = target.base.base

        def same(*args: str) -> str:
            return (
                "a" * 40
                if args[:2] in {("rev-parse", "HEAD"), ("rev-parse", "target/main")}
                else ""
            )

        with mock.patch.object(audit, "_git", side_effect=same), mock.patch.object(
            target, "_tests", return_value=self._fake_tests()
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
            audit, "_watchers", return_value=self._watchers()
        ), mock.patch.object(audit, "_lease_inactive", return_value=True):
            return target.build_audit(now=1, tracked=False)

    def test_dry_audit_only_authorizes_fresh_protocol_design(self) -> None:
        value = self._dry_value()
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["findings"], [])
        self.assertTrue(value["authorization"]["cran_semantic_transport_build_only"])
        self.assertTrue(value["authorization"]["fresh_semantic_transport_protocol_design"])
        self.assertFalse(value["authorization"]["public_snapshot_network_access_or_execution_start"])

    def test_resealed_nested_hidden_hash_capability_or_authority_tamper_fails(self) -> None:
        value = self._dry_value()
        locations = (
            (),
            ("git",),
            ("tests",),
            ("tests", "suites", 0),
            ("direct_capability_audit",),
            ("semantic_audit",),
            ("runtime_state",),
            (
                "runtime_state",
                "protected_watchers",
                str(next(iter(target.base.base.PROTECTED_WATCHERS))),
            ),
            ("checks",),
            ("authorization",),
        )
        for location in locations:
            changed = copy.deepcopy(value)
            container = changed
            for component in location:
                container = container[component]
            container["hidden_runtime_authority"] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(location=location), self.assertRaises(ValueError):
                target.validate_audit(changed)
        for kind in ("hash", "capability", "authority", "network", "alternate"):
            changed = copy.deepcopy(value)
            if kind == "hash":
                changed["fixed_artifact_hashes"][str(target.DESIGN)] = "0" * 64
            elif kind == "capability":
                changed["direct_capability_audit"]["closure_forbidden_imports"] = {}
            elif kind == "authority":
                changed["authorization"]["public_snapshot_network_access_or_execution_start"] = True
            elif kind == "network":
                changed["network_model_search_fetch_evaluator_benchmark_or_api_called"] = True
            else:
                changed["known_safe_alternate_mime_allowlist_count"] = 1
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
