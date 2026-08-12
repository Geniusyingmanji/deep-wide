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

from scripts import audit_v25217_single_snapshot_transport_build as target  # noqa: E402


class V25217SingleSnapshotTransportBuildAuditTests(unittest.TestCase):
    def test_fixed_hash_and_design_barriers(self) -> None:
        self.assertTrue(target._hash_barrier())
        self.assertTrue(target._design_barrier())

    def test_expected_suite_total_is_exact(self) -> None:
        self.assertEqual(target.EXPECTED_TESTS, 26)

    def test_direct_network_capability_is_disclosed_and_narrow(self) -> None:
        value = target._direct_capability()
        self.assertTrue(value["requests_and_socket_capability_present"])
        self.assertEqual(
            value["filesystem_process_environment_model_search_evaluator_imports"],
            [],
        )
        self.assertEqual(value["top_level_effect_calls"], [])

    def test_dependency_and_semantic_findings_are_zero_except_disclosed_network(self) -> None:
        closure = target.base.base._dependency_closure((target.TRANSPORT_SOURCE,))
        self.assertEqual(closure, (target.TRANSPORT_SOURCE,))
        semantic = target.base.base._semantic_findings(closure)
        self.assertEqual(semantic["privileged_runtime_field_accesses"], [])
        self.assertEqual(semantic["evaluator_capabilities"], [])
        self.assertEqual(semantic["credential_literal_hits"], [])

    def test_source_exposes_soft_deadline_and_unpinned_dns_limitations(self) -> None:
        source = target.base.base._ordinary(target.TRANSPORT_SOURCE).read_text(
            encoding="utf-8"
        )
        self.assertIn("dns_preflight_result_pinned_to_transport", source)
        self.assertIn("requests_timeout_is_hard_total_wall_deadline", source)
        self.assertIn("independent_hard_deadline_controller_required_for_execution", source)

    def test_resealed_authorization_capability_or_hash_tamper_fails(self) -> None:
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
        for kind in ("authorization", "capability", "hash"):
            changed = copy.deepcopy(value)
            if kind == "authorization":
                changed["authorization"]["public_snapshot_network_access_or_execution_start"] = True
            elif kind == "capability":
                changed["direct_capability_audit"]["top_level_effect_calls"] = ["fetch_snapshot"]
            else:
                changed["fixed_artifact_hashes"][str(target.DESIGN)] = "0" * 64
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
