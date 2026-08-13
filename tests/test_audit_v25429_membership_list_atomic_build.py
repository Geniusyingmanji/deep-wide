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

from scripts import audit_v25429_membership_list_atomic_build as target  # noqa: E402


class V25429MembershipListAtomicBuildAuditTests(unittest.TestCase):
    def test_parent_barriers_and_fixed_hashes_are_exact(self) -> None:
        diagnosed, selected, membership, listed = target._barriers()
        self.assertTrue(diagnosed["diagnosis_valid"])
        self.assertEqual(
            selected["selected_first_zero_intersection_interval"],
            "RFC 9240-9319",
        )
        self.assertTrue(membership["audit_valid"])
        self.assertTrue(listed["audit_valid"])
        self.assertTrue(
            all(
                target.base.sha256(path) == expected
                for path, expected in target.FIXED_HASHES.items()
            )
        )

    def test_runtime_closure_and_semantics_are_frozen(self) -> None:
        closure, vector = target._closure()
        self.assertEqual(len(closure), target.EXPECTED_CLOSURE_COUNT)
        self.assertEqual(
            target.base.payload_sha256(vector),
            target.EXPECTED_CLOSURE_VECTOR_SHA256,
        )
        self.assertEqual(
            target.base.payload_sha256([row["path"] for row in vector]),
            target.EXPECTED_CLOSURE_PATH_SHA256,
        )
        semantic = target.base._semantic_findings(closure)
        self.assertEqual(semantic["privileged_runtime_field_accesses"], [])
        self.assertEqual(semantic["evaluator_capabilities"], [])
        self.assertEqual(semantic["credential_literal_hits"], [])

    def test_audit_authorizes_only_fresh_external_protocol_design(self) -> None:
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
                "fresh_combined_shared_effect_external_protocol_design"
            ]
        )
        self.assertFalse(value["authorization"]["external_forward"])
        self.assertFalse(
            value["authorization"]["deepwidebench_forward_or_evaluator"]
        )

    def test_resealed_semantic_or_population_tamper_fails(self) -> None:
        tests = {
            "expected": target.EXPECTED_TESTS,
            "observed": target.EXPECTED_TESTS,
            "passed": True,
            "suites": [],
        }
        with mock.patch.object(target, "_tests", return_value=tests):
            value = target.build_audit(now=1, tracked=False)
        for kind in ("semantic", "population"):
            changed = copy.deepcopy(value)
            if kind == "semantic":
                changed["semantic_audit"]["evaluator_capabilities"] = ["x"]
            else:
                changed["population"]["selected_interval"] = "RFC 9160-9239"
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.base.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
