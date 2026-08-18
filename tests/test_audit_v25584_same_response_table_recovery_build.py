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

from scripts import audit_v25584_same_response_table_recovery_build as target  # noqa: E402


class V25584SameResponseTableRecoveryBuildAuditTests(unittest.TestCase):
    def test_fixed_hashes_closure_and_semantics(self) -> None:
        self.assertEqual(
            {str(path): target.base.sha256(path) for path in target.FIXED_HASHES},
            {
                str(path): expected
                for path, expected in target.FIXED_HASHES.items()
            },
        )
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

    def test_diagnosis_is_exact_and_design_only(self) -> None:
        value = target._diagnosis_barrier()
        self.assertTrue(value["diagnosis_valid"])
        self.assertEqual(value["findings"], [])
        self.assertEqual(
            value["fallback_diagnosis"]["joint_envelope_exact_tasks"], 6
        )
        self.assertEqual(
            value["fallback_diagnosis"]["joint_table_normalizable_tasks"], 0
        )
        self.assertFalse(value["authorization"]["external_forward"])
        self.assertFalse(
            value["authorization"]["deepwidebench_forward_or_evaluator"]
        )

    def test_watcher_observation_rejects_replacement(self) -> None:
        value = target._watcher_observation()
        self.assertTrue(value["same_frozen_identity"])
        self.assertFalse(value["replacement_process_observed"])
        self.assertFalse(
            value["agent_signal_stop_restart_or_replacement_performed"]
        )

    def test_audit_shape_is_fail_closed(self) -> None:
        head = target.base._git("rev-parse", "HEAD")
        with mock.patch.object(target, "_tests") as run_tests, mock.patch.object(
            target.base, "_git"
        ) as git, mock.patch.object(
            target.base, "_tracked", return_value=True
        ), mock.patch.object(
            target.base, "_lease_inactive", return_value=True
        ):
            run_tests.return_value = {
                "expected": target.EXPECTED_TESTS,
                "observed": target.EXPECTED_TESTS,
                "passed": True,
                "suites": [],
            }
            git.side_effect = lambda *args: (
                head
                if args[:2]
                in (("rev-parse", "HEAD"), ("rev-parse", "target/main"))
                else target.IMPLEMENTATION_COMMIT
                if args and args[0] == "rev-list"
                else ""
            )
            value = target.build_audit(now=1, tracked=False)
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["findings"], [])
        self.assertFalse(value["authorization"]["external_forward"])
        self.assertFalse(
            value["authorization"]["deepwidebench_forward_or_evaluator"]
        )

        changed = copy.deepcopy(value)
        changed["checks"]["same_response_zero_extra_effect_only"] = False
        changed["audit_payload_sha256"] = target.base.payload_sha256(
            {
                key: item
                for key, item in changed.items()
                if key != "audit_payload_sha256"
            }
        )
        with self.assertRaises(ValueError):
            target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
