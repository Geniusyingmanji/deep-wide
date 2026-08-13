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

from scripts import audit_v25420_list_atomic_changed_safe_build as target  # noqa: E402


class V25420ListAtomicChangedSafeBuildAuditTests(unittest.TestCase):
    def test_fixed_hashes_and_diagnosis_barrier(self) -> None:
        for path, expected in target.FIXED_HASHES.items():
            self.assertEqual(target.base.sha256(path), expected)
        value = target._diagnosis_barrier()
        self.assertTrue(value["authorization"]["list_atomic_guard_build"])
        self.assertFalse(
            value["authorization"]["reuse_current_population_for_candidate_validation"]
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

    def test_build_audit_shape_is_fail_closed(self) -> None:
        with mock.patch.object(target.base, "_test") as run_test, mock.patch.object(
            target.base, "_git"
        ) as git, mock.patch.object(
            target.watcher_contract, "watcher_snapshot"
        ) as watchers, mock.patch.object(
            target.base, "_tracked", return_value=True
        ), mock.patch.object(target.base, "_lease_inactive", return_value=True):
            run_test.side_effect = lambda pattern, expected: {
                "pattern": pattern,
                "expected": expected,
                "observed": expected,
                "returncode": 0,
                "output_sha256": "a" * 64,
                "passed": True,
            }

            def fake_git(*args):
                if args[:2] in (("rev-parse", "HEAD"), ("rev-parse", "target/main")):
                    return "a" * 40
                if args and args[0] == "rev-list":
                    return target.IMPLEMENTATION_COMMIT
                return ""

            git.side_effect = fake_git
            watchers.return_value = [
                {"pid": pid, "start_ticks": ticks, "marker": marker}
                for pid, ticks, marker in target.watcher_contract.EXPECTED_WATCHERS
            ]
            value = target.build_audit(now=1, tracked=False)
        self.assertTrue(value["audit_valid"])
        self.assertFalse(value["authorization"]["external_forward"])
        changed = copy.deepcopy(value)
        changed["checks"]["runtime_calls_v25375_parent_exactly_once"] = False
        changed["audit_payload_sha256"] = target.base.payload_sha256(
            {key: item for key, item in changed.items() if key != "audit_payload_sha256"}
        )
        with self.assertRaises(ValueError):
            target.validate_audit(changed)

    def test_authorization_stops_before_external_or_benchmark(self) -> None:
        self.assertEqual(target.EXPECTED_TESTS, 59)
        self.assertNotEqual(target.OUTPUT, target.DIAGNOSIS_ARTIFACT)


if __name__ == "__main__":
    unittest.main()
