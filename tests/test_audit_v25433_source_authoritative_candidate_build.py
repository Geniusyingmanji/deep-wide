from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25433_source_authoritative_candidate_build as target  # noqa: E402


class V25433SourceAuthoritativeCandidateBuildAuditTests(unittest.TestCase):
    def test_fixed_hashes_closure_and_semantics_are_exact(self) -> None:
        self.assertTrue(
            all(
                target.base.sha256(path) == expected
                for path, expected in target.FIXED_HASHES.items()
            )
        )
        closure, vector = target._closure()
        self.assertEqual(len(closure), target.EXPECTED_CLOSURE_COUNT)
        self.assertEqual(
            target.base.payload_sha256(vector),
            target.EXPECTED_CLOSURE_VECTOR_SHA256,
        )
        semantic = target.base._semantic_findings(closure)
        self.assertEqual(semantic["privileged_runtime_field_accesses"], [])
        self.assertEqual(semantic["evaluator_capabilities"], [])
        self.assertEqual(semantic["credential_literal_hits"], [])

    def test_build_audit_authorizes_only_fresh_protocol_design(self) -> None:
        tests = {
            "expected": target.EXPECTED_TESTS,
            "observed": target.EXPECTED_TESTS,
            "passed": True,
            "suites": [],
        }
        with mock.patch.object(target, "_tests", return_value=tests):
            value = target.build_audit(now=1, tracked=False)
        self.assertEqual(target.validate_audit(value), value)
        self.assertTrue(
            value["authorization"][
                "fresh_disjoint_source_authoritative_external_protocol_design"
            ]
        )
        self.assertFalse(value["authorization"]["external_forward"])
        self.assertFalse(
            value["authorization"]["deepwidebench_forward_or_evaluator"]
        )

    def test_resealed_semantic_effect_or_authorization_tamper_fails(self) -> None:
        tests = {
            "expected": target.EXPECTED_TESTS,
            "observed": target.EXPECTED_TESTS,
            "passed": True,
            "suites": [],
        }
        with mock.patch.object(target, "_tests", return_value=tests):
            value = target.build_audit(now=1, tracked=False)
        for kind in ("semantic", "effect", "authorization"):
            changed = copy.deepcopy(value)
            if kind == "semantic":
                changed["semantic_audit"]["evaluator_capabilities"] = ["x"]
            elif kind == "effect":
                changed["effect_delta"]["model_requests"] = 1
            else:
                changed["authorization"]["external_forward"] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.base.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)

    def test_test_denominator_and_no_launch_scope_are_frozen(self) -> None:
        self.assertEqual(target.EXPECTED_TESTS, 76)
        self.assertIn("build_audit", str(target.OUTPUT))
        self.assertNotIn("external", str(target.OUTPUT))
        self.assertNotIn("exact220", str(target.OUTPUT))


if __name__ == "__main__":
    unittest.main()
