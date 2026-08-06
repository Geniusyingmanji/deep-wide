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

from deepwide_agent.v24630_exact220_contract import payload_sha256  # noqa: E402
from scripts import v24633_neutral_capacity_stress as target  # noqa: E402


def successful_worker(ordinal: int) -> dict[str, object]:
    recoveries, repairs = target._effect_sets()
    stages = ["plan", "synthesis"]
    if ordinal in recoveries:
        stages.append("recovery")
    elif ordinal in repairs:
        stages.append("repair")
    scheduled = {name: stages.count(name) for name in stages}
    logical = len(stages)
    return {
        "logical_effects": logical,
        "successful_effects": logical,
        "failed_effects": 0,
        "stage_scheduled": scheduled,
        "stage_success": scheduled,
        "stage_failure": {},
        "stage_input_tokens": {
            name: count
            * (
                target.MIN_PLAN_INPUT_TOKENS_PER_SUCCESS + 10
                if name == "plan"
                else target.MIN_POSTPLAN_INPUT_TOKENS_PER_SUCCESS + 10
            )
            for name, count in scheduled.items()
        },
        "stage_output_tokens": {
            name: count
            * (
                target.MIN_PLAN_OUTPUT_TOKENS_PER_SUCCESS + 10
                if name == "plan"
                else target.MIN_POSTPLAN_OUTPUT_TOKENS_PER_SUCCESS + 10
            )
            for name, count in scheduled.items()
        },
        "stage_total_tokens": {
            name: count
            * (
                target.MIN_PLAN_INPUT_TOKENS_PER_SUCCESS
                + target.MIN_PLAN_OUTPUT_TOKENS_PER_SUCCESS
                + 20
                if name == "plan"
                else target.MIN_POSTPLAN_INPUT_TOKENS_PER_SUCCESS
                + target.MIN_POSTPLAN_OUTPUT_TOKENS_PER_SUCCESS
                + 20
            )
            for name, count in scheduled.items()
        },
        "provider_requests": logical,
        "provider_attempts": logical,
        "provider_successes": logical,
        "provider_failures": 0,
        "provider_deadline_failures": 0,
        "hard_total_wall_timeouts": 0,
        "input_tokens": sum(
            count
            * (
                target.MIN_PLAN_INPUT_TOKENS_PER_SUCCESS + 10
                if name == "plan"
                else target.MIN_POSTPLAN_INPUT_TOKENS_PER_SUCCESS + 10
            )
            for name, count in scheduled.items()
        ),
        "output_tokens": sum(
            count
            * (
                target.MIN_PLAN_OUTPUT_TOKENS_PER_SUCCESS + 10
                if name == "plan"
                else target.MIN_POSTPLAN_OUTPUT_TOKENS_PER_SUCCESS + 10
            )
            for name, count in scheduled.items()
        ),
        "total_tokens": sum(
            count
            * (
                target.MIN_PLAN_INPUT_TOKENS_PER_SUCCESS
                + target.MIN_PLAN_OUTPUT_TOKENS_PER_SUCCESS
                + 20
                if name == "plan"
                else target.MIN_POSTPLAN_INPUT_TOKENS_PER_SUCCESS
                + target.MIN_POSTPLAN_OUTPUT_TOKENS_PER_SUCCESS
                + 20
            )
            for name, count in scheduled.items()
        ),
        "slot_acquisitions": logical,
        "slot_timeouts": 0,
        "slot_total_wait_seconds": 1.0,
        "slot_max_wait_seconds": 0.5,
        "task_wall_seconds": 100.0,
        "effect_wall_seconds": 40.0,
        "deadline_exhausted": False,
    }


def successful_arm(arm: dict[str, object]) -> dict[str, object]:
    return target._aggregate_arm(
        arm,
        [successful_worker(index) for index in range(target.ANONYMOUS_JOBS)],
        wall_seconds=1000.0,
        maximum_active_workers=int(arm["active_child_cap"]),
    )


def failed_arm(arm: dict[str, object]) -> dict[str, object]:
    workers = [successful_worker(index) for index in range(target.ANONYMOUS_JOBS)]
    workers[0] = dict(workers[0])
    workers[0]["successful_effects"] = 1
    workers[0]["failed_effects"] = 1
    workers[0]["provider_successes"] = 1
    workers[0]["provider_failures"] = 1
    workers[0]["stage_success"] = {"plan": 1}
    workers[0]["stage_failure"] = {"synthesis": 1}
    for key in ("stage_input_tokens", "stage_output_tokens", "stage_total_tokens"):
        workers[0][key] = {"plan": workers[0][key]["plan"], "synthesis": 0}
    workers[0]["input_tokens"] = workers[0]["stage_input_tokens"]["plan"]
    workers[0]["output_tokens"] = workers[0]["stage_output_tokens"]["plan"]
    workers[0]["total_tokens"] = workers[0]["stage_total_tokens"]["plan"]
    return target._aggregate_arm(
        arm,
        workers,
        wall_seconds=1000.0,
        maximum_active_workers=int(arm["active_child_cap"]),
    )


class V24633NeutralCapacityStressTests(unittest.TestCase):
    def test_protocol_freezes_exact_shape_and_no_benchmark_launch(self) -> None:
        value = target.build_protocol(ROOT, now=1, require_pristine=False)
        self.assertEqual(value["scope"]["anonymous_jobs_per_arm"], 220)
        self.assertEqual(value["workload"]["total_logical_model_effects_per_arm"], 462)
        self.assertEqual(value["workload"]["total_logical_model_effects_all_arms"], 1848)
        self.assertEqual(len(value["arms"]), 4)
        self.assertEqual(value["arms"][1]["active_child_cap"], 20)
        self.assertEqual(value["arms"][1]["task_deadline_seconds"], 240)
        self.assertFalse(value["authorization"]["neutral_capacity_stress_launch"])
        self.assertFalse(value["authorization"]["benchmark_dev_or_exact220_launch"])

    def test_effect_assignment_matches_parent_simulation(self) -> None:
        recoveries, repairs = target._effect_sets()
        self.assertEqual(len(recoveries), 20)
        self.assertEqual(len(repairs), 2)
        self.assertFalse(recoveries.intersection(repairs))
        workers = [successful_worker(index) for index in range(220)]
        self.assertEqual(sum(value["logical_effects"] for value in workers), 462)

    def test_successful_arm_requires_exact_conservation(self) -> None:
        value = successful_arm(dict(target.ARMS[1]))
        self.assertTrue(value["mechanism_gate_passed"])
        self.assertEqual(value["slots"]["acquisitions"], 462)
        self.assertEqual(value["slots"]["timeouts"], 0)
        failed = failed_arm(dict(target.ARMS[1]))
        self.assertFalse(failed["mechanism_gate_passed"])
        self.assertEqual(failed["failed_jobs"], 1)

    def test_result_gate_ignores_control_failure_but_not_candidate_failure(self) -> None:
        arms = [successful_arm(dict(arm)) for arm in target.ARMS]
        arms[0] = failed_arm(dict(target.ARMS[0]))
        value = target.project_result(
            arms, execution_start_sha256="a" * 64, wall_seconds=4000, now=1
        )
        self.assertTrue(value["mechanism_gate_passed"])
        self.assertIn(target.ARM_NAMES[1], value["passing_candidate_arms"])
        for index in range(1, 4):
            arms[index] = failed_arm(dict(target.ARMS[index]))
        failed = target.project_result(
            arms, execution_start_sha256="a" * 64, wall_seconds=4000, now=1
        )
        self.assertFalse(failed["mechanism_gate_passed"])

    def test_result_tamper_is_rejected_and_content_free(self) -> None:
        arms = [successful_arm(dict(arm)) for arm in target.ARMS]
        value = target.project_result(
            arms, execution_start_sha256="a" * 64, wall_seconds=4000, now=1
        )
        encoded = json.dumps(value, ensure_ascii=False)
        self.assertIsNone(target.SECRET.search(encoded))
        self.assertIsNone(target.OPAQUE.search(encoded))
        altered = copy.deepcopy(value)
        altered["authorization"]["benchmark_dev_or_exact220_launch"] = True
        altered.pop("result_payload_sha256")
        altered["result_payload_sha256"] = payload_sha256(altered)
        with self.assertRaisesRegex(RuntimeError, "result drifted"):
            target.validate_result(altered)

    def test_source_has_no_privileged_access_or_benchmark_execution_call(self) -> None:
        accesses, calls = target._source_findings(ROOT, target.SOURCE)
        self.assertEqual(accesses, [])
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
