from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import v24345_semantic_active_natural_admission as target  # noqa: E402


def task_projection(
    ordinal: int,
    *,
    eligible: bool = False,
    nonidentity: bool = False,
    passed: bool = True,
) -> dict:
    value = {
        "ordinal": ordinal,
        "wall_seconds": 30.0,
        "parent_taxonomy": "success",
        "all_parent_artifacts_valid": True,
        "result_status": "completed",
        "completion_kind": "paired" if nonidentity else "identity_no_reserve",
        "effect_accounting_complete": True,
        "prefix_status": "frozen",
        "prefix_producer_execution_count": 1,
        "logical_model_admissions": 3 if eligible else 2,
        "provider_model_requests": 3 if eligible else 2,
        "provider_model_attempts": 3 if eligible else 2,
        "pre_provider_model_rejections": 0,
        "slot_acquisitions": 3 if eligible else 2,
        "slot_timeouts": 0,
        "provider_deadline_failures": 0,
        "slot_total_wait_seconds": 5.0,
        "slot_max_wait_seconds": 2.0,
        "slot_acquisition_counts": [2, 1] if eligible else [1, 1],
        "core_logical_queries": 4,
        "search_provider_effects": 1,
        "core_fetch_targets": 7,
        "reserve_fetch_targets": 3,
        "core_usable_pages": 7,
        "reserve_usable_pages": 3,
        "repeated_upstream_effects": 0,
        "catalog_status": "built_eligible" if eligible else "built_empty",
        "shared_raw_pages": True,
        "fetch_before_baseline": True,
        "candidate_only_structure": True,
        "core_page_count": 7,
        "reserve_page_count": 3,
        "semantic_projection_count": 2,
        "eligible_support_set_count": 1 if eligible else 0,
        "eligible_support_scope_counts": {"mixed": 1} if eligible else {},
        "revision_model_admitted": eligible,
        "revision_model_returned": eligible,
        "revision_gate_applied": eligible,
        "third_model_call_skipped_no_eligible_support": not eligible,
        "candidate_identity_handoff": not nonidentity,
        "proposed_cell_changes": 1 if eligible else 0,
        "admitted_cell_changes": 1 if nonidentity else 0,
        "entropy_positive": nonidentity,
        "admitted_support_scope_counts": {"mixed": 1} if nonidentity else {},
        "gate_private_replay_present": True,
        "private_replay_valid": True,
        "model_requests": 3 if eligible else 2,
        "model_attempts": 3 if eligible else 2,
        "model_total_tokens": 100,
        "search_calls": 1,
        "fetch_calls": 10,
        "fetch_failures": 0,
        "search_total_tokens": 200,
        "hosted_search_deadline_failures": 0,
        "hard_fetch_helper_calls": 10,
        "hard_fetch_deadline_failures": 0,
        "fetch_deadline_rejections": 0,
        "fetch_helper_failures": 0,
        "deadline_exhausted": False,
    }
    value["checks"] = target._task_checks(value)
    if not passed:
        value["checks"]["deadline_not_exhausted"] = False
    value["passed"] = all(value["checks"].values())
    target.validate_task_projection(value)
    return value


class V24345SemanticActiveNaturalAdmissionTests(unittest.TestCase):
    def test_fixed_tasks_are_visible_only_and_protocol_is_content_free(self) -> None:
        tasks = [target.neutral_task(index) for index in range(1, 13)]
        self.assertEqual(len({task["opaque_id"] for task in tasks}), 12)
        protocol = target.build_protocol(ROOT, now=0, require_pristine=False)
        target.validate_protocol(ROOT, value=protocol)
        encoded = json.dumps(protocol, ensure_ascii=False)
        for task in tasks:
            self.assertNotIn(task["question"], encoded)
            self.assertNotIn(task["opaque_id"], encoded)

    def test_one_natural_admission_satisfies_mechanism_gate(self) -> None:
        values = [task_projection(index) for index in range(1, 13)]
        values[0] = task_projection(1, eligible=True, nonidentity=True)
        aggregate = target.aggregate_tasks(values, 60.0)
        self.assertTrue(aggregate["passed"])
        self.assertEqual(aggregate["candidate_nonidentity_tasks"], 1)
        self.assertEqual(aggregate["admitted_cell_changes"], 1)
        self.assertEqual(aggregate["entropy_positive_tasks"], 1)

    def test_zero_natural_admission_is_strict_no_go(self) -> None:
        aggregate = target.aggregate_tasks(
            [task_projection(index) for index in range(1, 13)], 60.0
        )
        self.assertFalse(aggregate["passed"])
        for check in (
            "eligible_support_tasks",
            "revision_admitted_tasks",
            "candidate_nonidentity_tasks",
            "admitted_cell_changes",
            "entropy_positive_tasks",
        ):
            self.assertFalse(aggregate["checks"][check])

    def test_failed_task_and_tampered_projection_are_rejected(self) -> None:
        values = [task_projection(index) for index in range(1, 13)]
        values[0] = task_projection(1, eligible=True, nonidentity=True)
        values[-1] = task_projection(12, passed=False)
        self.assertFalse(target.aggregate_tasks(values, 60.0)["passed"])
        altered = task_projection(1, eligible=True, nonidentity=True)
        altered["slot_acquisition_counts"] = [3, 3]
        with self.assertRaises(RuntimeError):
            target.validate_task_projection(altered)

    def test_preaudit_fails_on_port_lease_or_dirty_worktree(self) -> None:
        protocol = target.build_protocol(ROOT, now=0, require_pristine=False)
        common = (
            patch.object(target, "validate_protocol", return_value=protocol),
            patch.object(target, "_run_test", return_value=True),
            patch.object(target, "sha256", return_value="a" * 64),
            patch.object(target, "_future", return_value=True),
            patch.object(target, "protected_watcher_snapshot", return_value=[]),
        )
        with common[0], common[1], common[2], common[3], common[4], patch.object(
            target, "_port_listening", return_value=False
        ), patch.object(target, "lease_observation", return_value={"active": False}), patch.object(
            target, "_git", side_effect=lambda root, *args: ""
        ):
            with self.assertRaises(RuntimeError):
                target.build_preaudit(ROOT, now=0)


if __name__ == "__main__":
    unittest.main()
