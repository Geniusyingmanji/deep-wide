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

from deepwide_agent.v24257_score_first_runtime import validate_visible_task  # noqa: E402
from scripts import v24302_neutral_concurrent_synthesis_recovery as target  # noqa: E402
from tests.test_v24301_neutral_concurrent_synthesis_recovery import (  # noqa: E402
    successful_worker,
)


class V24302NeutralConcurrentSynthesisRecoveryTests(unittest.TestCase):
    def test_parent_failure_is_reproducible_before_any_effect(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid opaque task identifier"):
            validate_visible_task(target.parent.neutral_task(1))
        lease = {
            "owner": "v24301_neutral_concurrent_synthesis_recovery_probe_v1",
            "purpose": "neutral_concurrent_real_provider_bounded_synthesis_recovery",
            "active": False,
            "pid": 123,
            "acquired_at_unix": 1,
            "released_at_unix": 1,
        }
        watchers = [
            {"pid": pid, "marker": marker, "start_ticks": 1}
            for pid, marker in target.PROTECTED_WATCHERS.items()
        ]
        failure = target.build_failure_receipt(
            ROOT, now=1, lease_record=lease, protected_watchers=watchers
        )
        self.assertTrue(all(value == 0 for value in failure["effect_ledger"].values()))
        self.assertEqual(failure["shared_api_lease"]["acquisitions"], 1)
        self.assertFalse(failure["same_protocol_retry_or_resume_authorized"])
        self.assertTrue(failure["new_versioned_successor_required"])

    def test_all_corrected_tasks_pass_real_visible_boundary(self) -> None:
        identities = set()
        for index in range(1, 9):
            task = target.corrected_neutral_task(index)
            self.assertEqual(set(task), {"opaque_id", "question"})
            self.assertEqual(validate_visible_task(task), task)
            identities.add(task["opaque_id"])
        self.assertEqual(len(identities), 8)

    def test_protocol_is_single_change_and_has_no_benchmark_authority(self) -> None:
        with mock.patch.object(
            target,
            "_failure",
            return_value={"failure_payload_sha256": "f" * 64},
        ), mock.patch.object(target, "sha256", return_value="a" * 64):
            protocol = target.build_protocol(ROOT, now=1, require_pristine=False)
        self.assertTrue(
            protocol["correction"][
                "all_eight_corrected_tasks_pass_validate_visible_task_before_activation"
            ]
        )
        self.assertFalse(protocol["correction"]["parent_protocol_retry_or_resume"])
        self.assertEqual(protocol["budget_contract"]["model_calls_total"], 24)
        self.assertFalse(protocol["authorization"]["benchmark_dev64_launch"])
        self.assertFalse(protocol["authorization"]["exact220_launch"])

    def test_success_projection_requires_visible_task_validation_gate(self) -> None:
        value = target.project(
            [successful_worker(index) for index in range(1, 9)],
            wall_seconds=2.0,
            barrier_broken=False,
            now=1,
        )
        self.assertTrue(all(target._checks(value, target.GATES).values()))
        altered = copy.deepcopy(value)
        altered["validated_visible_tasks_before_effect"] = 7
        unsigned = dict(altered)
        unsigned.pop("result_payload_sha256")
        altered["result_payload_sha256"] = target.payload_sha256(unsigned)
        with self.assertRaises(RuntimeError):
            target.validate_projection(altered)

    def test_one_failed_recovery_still_fails_gate(self) -> None:
        workers = [successful_worker(index) for index in range(1, 9)]
        workers[-1]["completion_kind"] = "best_effort_fallback"
        workers[-1]["recovery"]["recovery_succeeded"] = False
        workers[-1]["recovery"]["recovery_model_request_error"] = True
        workers[-1]["recovery"]["real_recovery_requests"] = 0
        value = target.project(
            workers, wall_seconds=2.0, barrier_broken=False, now=1
        )
        checks = target._checks(value, target.GATES)
        self.assertFalse(checks["primary_tasks"])
        self.assertFalse(checks["recovery_successes"])


if __name__ == "__main__":
    unittest.main()
