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

from scripts import audit_v25390_hybrid_record_fallback_build as target  # noqa: E402


class V25390HybridRecordFallbackBuildAuditTests(unittest.TestCase):
    def test_fixed_runtime_test_and_diagnosis_hashes(self) -> None:
        for path, expected in target.FIXED_HASHES.items():
            self.assertEqual(target.base.sha256(path), expected)

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
        ), mock.patch.object(
            target.base, "_lease_inactive", return_value=True
        ), mock.patch.object(
            target, "_port_reachable", return_value=True
        ):
            run_test.side_effect = lambda pattern, expected: {
                "pattern": pattern,
                "expected": expected,
                "observed": expected,
                "returncode": 0,
                "output_sha256": "a" * 64,
                "passed": True,
            }
            git.side_effect = lambda *args: (
                "a" * 40
                if args[:2]
                in (("rev-parse", "HEAD"), ("rev-parse", "target/main"))
                else ""
            )
            watchers.return_value = [
                {"pid": pid, "start_ticks": ticks, "marker": marker}
                for pid, ticks, marker in target.watcher_contract.EXPECTED_WATCHERS
            ]
            value = target.build_audit(now=1, tracked=False)
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["findings"], [])
        self.assertFalse(value["authorization"]["external_forward"])
        changed = copy.deepcopy(value)
        changed["checks"]["invalid_joint_cannot_fall_through_to_valid_grounded"] = False
        changed["audit_payload_sha256"] = target.base.payload_sha256(
            {key: item for key, item in changed.items() if key != "audit_payload_sha256"}
        )
        with self.assertRaises(ValueError):
            target.validate_audit(changed)

    def test_diagnosis_only_authorizes_next_build(self) -> None:
        value = target._diagnosis_barrier()
        self.assertTrue(
            value["authorization"][
                "hybrid_joint_or_grounded_record_fallback_build_only"
            ]
        )
        self.assertFalse(value["authorization"]["new_external_forward"])
        self.assertFalse(value["entropy_or_information_gain_assigns_signed_credit"])


if __name__ == "__main__":
    unittest.main()
