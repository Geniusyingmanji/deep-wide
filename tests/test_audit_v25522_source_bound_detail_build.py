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

from scripts import audit_v25522_source_bound_detail_build as target  # noqa: E402


class V25522SourceBoundDetailBuildAuditTests(unittest.TestCase):
    def test_fixed_hashes_commits_and_diagnosis_barrier_are_exact(self) -> None:
        self.assertTrue(target._diagnosis_barrier())
        self.assertTrue(
            all(
                target.base.sha256(path) == digest
                for path, digest in target.FIXED_HASHES.items()
            )
        )
        history = set(
            target.base._git(
                "rev-list", target.base._git("rev-parse", "HEAD")
            ).splitlines()
        )
        self.assertTrue(
            all(commit in history for commit in target.IMPLEMENTATION_COMMITS)
        )

    def test_closure_count_and_hash_are_frozen(self) -> None:
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

    def test_build_audit_passes_without_external_effect(self) -> None:
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
            value["authorization"][
                "fresh_task_disjoint_external_population_design"
            ]
        )
        self.assertFalse(value["authorization"]["external_protocol_or_forward"])
        self.assertEqual(
            value["effect_delta_beyond_v25514"],
            {
                "model_requests": 0,
                "logical_queries": 0,
                "search_calls": 0,
                "fetch_calls": 0,
                "provider_tokens": 0,
            },
        )

    def test_resealed_credit_launch_or_effect_tamper_fails(self) -> None:
        tests = {
            "expected": target.EXPECTED_TESTS,
            "observed": target.EXPECTED_TESTS,
            "passed": True,
            "suites": [],
        }
        with mock.patch.object(target, "_tests", return_value=tests):
            value = target.build_audit(now=1, tracked=False)
        for kind in ("credit", "launch", "effect"):
            changed = copy.deepcopy(value)
            if kind == "credit":
                changed["positive_signed_credit_count"] = 1
            elif kind == "launch":
                changed["authorization"]["external_protocol_or_forward"] = True
            else:
                changed["effect_delta_beyond_v25514"]["fetch_calls"] = 1
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.base.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
