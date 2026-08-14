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

from scripts import audit_v25546_deterministic_visible_constraint_build as target  # noqa: E402


class V25546DeterministicVisibleConstraintBuildAuditTests(unittest.TestCase):
    def test_fixed_hashes_commit_and_parent_barrier_are_exact(self) -> None:
        self.assertTrue(target._parent_barrier())
        self.assertTrue(all(target.base.sha256(path) == digest for path, digest in target.FIXED_HASHES.items()))
        history = set(target.base._git("rev-list", target.base._git("rev-parse", "HEAD")).splitlines())
        self.assertIn(target.IMPLEMENTATION_COMMIT, history)

    def test_closure_count_and_hash_are_frozen(self) -> None:
        closure, vector = target._closure()
        self.assertEqual(len(closure), target.EXPECTED_CLOSURE_COUNT)
        self.assertEqual(target.base.payload_sha256(vector), target.EXPECTED_CLOSURE_VECTOR_SHA256)
        self.assertEqual(target.base.payload_sha256([row["path"] for row in vector]), target.EXPECTED_CLOSURE_PATH_SHA256)

    def test_build_audit_passes_without_external_effect(self) -> None:
        tests = {"expected": target.EXPECTED_TESTS, "observed": target.EXPECTED_TESTS, "passed": True, "suites": []}
        with mock.patch.object(target, "_tests", return_value=tests):
            value = target.build_audit(now=1, tracked=False)
        self.assertEqual(target.validate_audit(value), value)
        self.assertTrue(value["audit_valid"])
        self.assertTrue(value["authorization"]["fresh_task_disjoint_shared_parent_population_design"])
        self.assertFalse(value["authorization"]["external_population_protocol_or_forward"])

    def test_resealed_contract_effect_or_authority_tamper_fails(self) -> None:
        tests = {"expected": target.EXPECTED_TESTS, "observed": target.EXPECTED_TESTS, "passed": True, "suites": []}
        with mock.patch.object(target, "_tests", return_value=tests):
            value = target.build_audit(now=1, tracked=False)
        for kind in ("credit", "launch", "effect", "operation", "runtime", "watcher", "closure"):
            changed = copy.deepcopy(value)
            if kind == "credit":
                changed["positive_signed_credit_count"] = 1
            elif kind == "launch":
                changed["authorization"]["external_population_protocol_or_forward"] = True
            elif kind == "effect":
                changed["effect_delta_beyond_v25401"]["model_requests"] = 1
            elif kind == "operation":
                changed["primitive_contract"]["temporal_range_row_filtering"] = True
            elif kind == "runtime":
                changed["runtime_contract"]["normal_path_model_forwards"] = 4
            elif kind == "watcher":
                changed["protected_watchers"][0]["start_ticks"] += 1
            else:
                changed["runtime_dependency_vector"][0]["sha256"] = "0" * 64
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.base.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
