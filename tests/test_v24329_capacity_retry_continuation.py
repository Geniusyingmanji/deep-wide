from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import v24328_shared_prefix_capacity_staircase as old  # noqa: E402
from scripts import v24329_capacity_retry_continuation as target  # noqa: E402
from test_v24328_shared_prefix_capacity_staircase import task  # noqa: E402


class V24329CapacityRetryContinuationTests(unittest.TestCase):
    def test_frozen_parent_failure_is_exactly_one_provider_retry(self) -> None:
        evidence = target._parent_evidence(ROOT)
        failed = [
            name
            for name, passed in evidence["task"]["checks"].items()
            if not passed
        ]
        self.assertEqual(failed, ["no_model_retry"])
        self.assertEqual(evidence["task"]["provider_model_requests"], 3)
        self.assertEqual(evidence["task"]["provider_model_attempts"], 4)

    def test_corrected_check_accepts_bounded_retry_and_preserves_cost(self) -> None:
        value = task(1)
        value["provider_model_attempts"] = 4
        value["model_attempts"] = 4
        value["checks"] = old._task_checks(value)
        value["passed"] = all(value["checks"].values())
        old.validate_task_projection(value)
        self.assertFalse(value["passed"])
        corrected = target.corrected_task_projection(value)
        self.assertTrue(corrected["passed"])
        self.assertEqual(corrected["provider_model_attempts"], 4)
        self.assertEqual(corrected["model_attempts"], 4)
        self.assertNotIn("no_model_retry", corrected["checks"])
        self.assertTrue(
            corrected["checks"]["provider_attempts_within_frozen_retry_budget"]
        )

    def test_retry_beyond_frozen_budget_fails(self) -> None:
        value = task(1)
        value["provider_model_attempts"] = 10
        value["model_attempts"] = 10
        value["checks"] = old._task_checks(value)
        value["passed"] = all(value["checks"].values())
        old.validate_task_projection(value)
        corrected = target.corrected_task_projection(value)
        self.assertFalse(corrected["passed"])
        self.assertFalse(
            corrected["checks"]["provider_attempts_within_frozen_retry_budget"]
        )

    def test_inherited_level_one_is_passing_and_not_reexecuted(self) -> None:
        level = target.inherited_level_one(ROOT)
        self.assertTrue(level["passed"])
        self.assertEqual(level["executor_count"], 1)
        self.assertEqual(level["tasks"][0]["provider_model_attempts"], 4)

    def test_result_origins_prohibit_level_one_remote_rerun(self) -> None:
        activation = {"protected_watchers": target.protected_watcher_snapshot()}
        levels = [target.inherited_level_one(ROOT)]
        for level in target.REMOTE_LEVELS:
            levels.append(
                old.summarize_level(
                    level=level,
                    tasks=[task(index) for index in range(1, level + 1)],
                    batch_wall_seconds=20.0 + level,
                )
            )
        value = target.build_result(levels=levels, activation=activation, now=0)
        self.assertTrue(value["all_requested_levels_passed"])
        self.assertFalse(value["level_one_remote_effect_repeated"])
        self.assertEqual(
            value["level_execution_origins"]["1"],
            "v24328_frozen_content_free_projection_no_remote_rerun",
        )
        self.assertTrue(
            value["authorization"][
                "fresh_shared_prefix_paired_benchmark_protocol_design"
            ]
        )

    def test_failed_level_stops_authority_and_resealed_exact220_is_rejected(self) -> None:
        activation = {"protected_watchers": target.protected_watcher_snapshot()}
        inherited = target.inherited_level_one(ROOT)
        failed_task = task(2, passed=False)
        failed_level = old.summarize_level(
            level=2,
            tasks=[task(1), failed_task],
            batch_wall_seconds=30.0,
        )
        value = target.build_result(
            levels=[inherited, failed_level], activation=activation, now=0
        )
        self.assertFalse(value["all_requested_levels_passed"])
        altered = copy.deepcopy(value)
        altered["authorization"]["exact220"] = True
        altered.pop("result_payload_sha256")
        altered["result_payload_sha256"] = payload_sha256(altered)
        with self.assertRaises(RuntimeError):
            target.validate_result(altered)

    def test_protocol_is_append_only_content_free_and_launch_false(self) -> None:
        value = target.build_protocol(ROOT, now=0, require_pristine=False)
        target.validate_protocol(ROOT, value=value)
        self.assertEqual(
            value["continuation_contract"]["new_remote_levels"], [2, 4, 8]
        )
        self.assertFalse(
            value["continuation_contract"]["level_one_remote_effect_repeated"]
        )
        self.assertFalse(value["authorization"]["capacity_continuation_launch"])
        encoded = json.dumps(value, ensure_ascii=False)
        self.assertIsNone(target.OPAQUE.search(encoded))
        self.assertFalse(any(item in encoded for item in old.CONTENT_LITERALS))


if __name__ == "__main__":
    unittest.main()
