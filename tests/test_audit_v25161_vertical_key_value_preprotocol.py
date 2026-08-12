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
    audit_v25161_vertical_key_value_preprotocol as target,
)


class V25161VerticalKeyValuePreprotocolAuditTests(unittest.TestCase):
    def test_parent_build_and_population_barriers(self) -> None:
        self.assertTrue(target._build_barrier())
        self.assertTrue(target._population_barrier())

    def test_runtime_and_parent_hashes_are_exact(self) -> None:
        audit = target.build_parent.audit_parent
        self.assertEqual(
            audit.sha256(target.RUNTIME_SOURCE), target.EXPECTED_RUNTIME_HASH
        )
        self.assertEqual(
            audit.sha256(target.BUILD_AUDIT),
            target.EXPECTED_BUILD_AUDIT_HASH,
        )
        self.assertEqual(
            audit.sha256(target.POPULATION_AUDIT),
            target.EXPECTED_POPULATION_AUDIT_HASH,
        )

    def test_expected_suite_total_is_exact(self) -> None:
        self.assertEqual(target.EXPECTED_TESTS, 24)

    def test_success_authorizes_protocol_design_only(self) -> None:
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

        audit = target.build_parent.audit_parent
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
        self.assertTrue(
            value["authorization"]["fresh_disjoint_external_protocol_design"]
        )
        self.assertFalse(
            value["authorization"]["fresh_external_activation_or_launch"]
        )
        self.assertFalse(
            value["authorization"]["evaluator_or_deepwidebench_or_sota"]
        )

    def test_resealed_authority_hash_or_credit_tamper_fails(self) -> None:
        fake_tests = {
            "expected": target.EXPECTED_TESTS,
            "observed": target.EXPECTED_TESTS,
            "passed": True,
            "suites": [],
        }
        audit = target.build_parent.audit_parent
        with mock.patch.object(
            audit,
            "_git",
            side_effect=lambda *args: "same"
            if args[:2]
            in {
                ("rev-parse", "HEAD"),
                ("rev-parse", "target/main"),
            }
            else "",
        ), mock.patch.object(
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
        for kind in ("activation", "evaluator", "reuse", "credit", "hash"):
            changed = copy.deepcopy(value)
            if kind == "activation":
                changed["authorization"][
                    "fresh_external_activation_or_launch"
                ] = True
            elif kind == "evaluator":
                changed["authorization"][
                    "evaluator_or_deepwidebench_or_sota"
                ] = True
            elif kind == "reuse":
                changed["authorization"][
                    "v25141_v25145_v25149_v25153_v25157_population_reuse"
                ] = True
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            else:
                changed["population_audit"]["sha256"] = "0" * 64
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
