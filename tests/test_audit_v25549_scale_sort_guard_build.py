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

from scripts import audit_v25549_scale_sort_guard_build as target  # noqa: E402


class V25549ScaleSortGuardBuildAuditTests(unittest.TestCase):
    def test_population_barrier_and_fixed_hashes_are_exact(self) -> None:
        self.assertTrue(target._population_barrier())
        self.assertTrue(
            all(
                target.base.sha256(path) == digest
                for path, digest in target.FIXED_HASHES.items()
            )
        )

    def test_closure_count_and_hashes_are_frozen(self) -> None:
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

    def test_build_audit_authorizes_external_gate_build_only(self) -> None:
        tests = {
            "expected": target.EXPECTED_TESTS,
            "observed": target.EXPECTED_TESTS,
            "passed": True,
            "suites": [],
        }
        with mock.patch.object(target, "_tests", return_value=tests):
            value = target.build_audit(now=1, tracked=False)
        self.assertEqual(target.validate_audit(value), value)
        self.assertTrue(value["audit_valid"])
        self.assertTrue(
            value["authorization"]["fresh_shared_parent_external_gate_build"]
        )
        self.assertFalse(value["authorization"]["external_protocol_or_forward"])

    def test_resealed_guard_contract_effect_or_authority_tamper_fails(self) -> None:
        tests = {
            "expected": target.EXPECTED_TESTS,
            "observed": target.EXPECTED_TESTS,
            "passed": True,
            "suites": [],
        }
        with mock.patch.object(target, "_tests", return_value=tests):
            value = target.build_audit(now=1, tracked=False)
        for kind in ("guard", "runtime", "effect", "credit", "authority", "closure"):
            changed = copy.deepcopy(value)
            if kind == "guard":
                changed["primitive_contract"]["scale_converted_column_sorting"] = True
            elif kind == "runtime":
                changed["runtime_contract"]["normal_path_model_forwards"] = 4
            elif kind == "effect":
                changed["effect_delta_beyond_v25401"]["fetch_calls"] = 1
            elif kind == "credit":
                changed["positive_signed_credit_count"] = 1
            elif kind == "authority":
                changed["authorization"]["external_protocol_or_forward"] = True
            else:
                changed["runtime_dependency_vector"][0]["sha256"] = "0" * 64
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.base.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
