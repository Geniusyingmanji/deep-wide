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

from scripts import (  # noqa: E402
    audit_v25576_canonical_column_totality_build as target,
)


class V25576CanonicalColumnTotalityBuildAuditTests(unittest.TestCase):
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

    def test_diagnosis_and_full_runtime_replay_claim_are_exact(self) -> None:
        value = target._diagnosis_barrier()
        self.assertTrue(value["diagnosis_valid"])
        self.assertEqual(value["findings"], [])
        replay = target._replay_claim()
        self.assertEqual(replay["task_count"], 220)
        self.assertEqual(replay["predecessor_failure_count"], 11)
        self.assertEqual(replay["successor_terminal_count"], 220)
        self.assertEqual(replay["successor_failure_count"], 0)
        self.assertEqual(
            replay["successor_mode_counts"],
            {
                "canonical_projection": 209,
                "byte_exact_parent_handoff": 0,
                "canonical_column_handoff": 11,
            },
        )
        self.assertFalse(
            replay[
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
            ]
        )

    def test_watcher_observation_accepts_absence_but_not_replacement(self) -> None:
        with mock.patch.object(Path, "is_file", return_value=False):
            value = target._watcher_observation(Path("/synthetic-proc"))
        self.assertEqual(value["audit_time_absent_count"], 4)
        self.assertEqual(value["replacement_process_count"], 0)
        self.assertFalse(
            value["agent_signal_stop_restart_or_replacement_performed"]
        )

    def test_audit_shape_is_fail_closed(self) -> None:
        with mock.patch.object(target, "_tests") as run_tests, mock.patch.object(
            target.base, "_git"
        ) as git, mock.patch.object(
            target.base, "_tracked", return_value=True
        ), mock.patch.object(
            target.base, "_lease_inactive", return_value=True
        ), mock.patch.object(
            target, "_watcher_observation"
        ) as watchers:
            run_tests.return_value = {
                "expected": target.EXPECTED_TESTS,
                "observed": target.EXPECTED_TESTS,
                "passed": True,
                "suites": [],
            }
            git.side_effect = lambda *args: (
                target.IMPLEMENTATION_COMMIT
                if args[:2]
                in (("rev-parse", "HEAD"), ("rev-parse", "target/main"))
                else target.IMPLEMENTATION_COMMIT
                if args and args[0] == "rev-list"
                else ""
            )
            watchers.return_value = {
                "turn_start_expected_count": 4,
                "audit_time_present_count": 1,
                "audit_time_same_identity_count": 1,
                "audit_time_absent_count": 3,
                "replacement_process_count": 0,
                "agent_signal_stop_restart_or_replacement_performed": False,
                "rows": [],
            }
            value = target.build_audit(now=1, tracked=False)
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["findings"], [])
        self.assertFalse(value["authorization"]["external_forward"])
        self.assertFalse(
            value["authorization"]["deepwidebench_forward_or_evaluator"]
        )

        changed = copy.deepcopy(value)
        changed["checks"][
            "full220_runtime_replay_successor_terminal_exact220"
        ] = False
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
