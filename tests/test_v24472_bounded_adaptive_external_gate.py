from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import v24472_bounded_adaptive_external_gate as target  # noqa: E402


def _seal(value: dict, field: str) -> dict:
    value.pop(field, None)
    value[field] = payload_sha256(value)
    return value


def _successful_public_result() -> dict:
    mechanism = {
        "selected": target.SELECTED,
        "exact_ordinal_vector": True,
        "passed_tasks": target.SELECTED,
        "failed_tasks": 0,
        "all_threshold_partitions_exact": True,
        "all_effects_conserved": True,
        "all_single_validation_attested": True,
        "all_projections_consumed_validated_capabilities": True,
        "total_adaptive_safe_change_count": 1,
        "total_adaptive_additional_fetch_calls": target.SELECTED,
        "total_adaptive_final_decision_credit_total_nats": 1.0,
    }
    observation = {
        "selected": target.SELECTED,
        "exact_ordinal_vector": True,
        "success_tasks": target.SELECTED,
        "failure_tasks": 0,
        "fully_observed_effect_tasks": target.SELECTED,
        "slot_timeouts_lower_bound": 0,
        "provider_deadline_failures_lower_bound": 0,
        "hosted_search_deadline_failures_lower_bound": 0,
        "hard_fetch_deadline_failures_lower_bound": 0,
        "fetch_helper_failures_lower_bound": 0,
        "unobserved_effect_tasks": 0,
    }
    timing = {
        "selected": target.SELECTED,
        "exact_ordinal_vector": True,
        "parent_success_tasks": target.SELECTED,
        "certificate_validation_invocations": target.SELECTED,
        "adaptive_projection_invocations": target.SELECTED,
        "recursive_historical_semantic_replay_tasks": 0,
        "parent_certificate_validation_wall_p95_seconds": 0.02,
    }
    supervision = {
        "selected": target.SELECTED,
        "exact_ordinal_vector": True,
        "worker_success_tasks": target.SELECTED,
        "worker_hard_timeout_tasks": 0,
        "worker_nonzero_tasks": 0,
        "checkpoint_chain_valid_tasks": target.SELECTED,
        "complete_validation_returned_tasks": target.SELECTED,
        "worker_wall_max_seconds": 100.0,
    }
    value = {
        "artifact_version": 1,
        "role": "v24472_bounded_adaptive_external_result",
        "protocol_id": target.PROTOCOL_ID,
        "created_at_unix": 0,
        "selected": target.SELECTED,
        "executor_count": target.EXECUTOR_COUNT,
        "model_slot_cap": target.MODEL_SLOT_CAP,
        "effect_deadline_seconds": target.EFFECT_DEADLINE_SECONDS,
        "worker_timeout_seconds": target.WORKER_TIMEOUT_SECONDS,
        "parent_timeout_seconds": target.PARENT_TIMEOUT_SECONDS,
        "one_wave": True,
        "batch_wall_seconds": 100.0,
        "mechanism_aggregate": mechanism,
        "observation_aggregate": observation,
        "stage_timing_aggregate": timing,
        "supervision_aggregate": supervision,
        "mechanism_failure_as_zero_rows": 0,
        "mechanism_passed": True,
        "reliability_passed": True,
        "parent_validation_passed": True,
        "latency_passed": True,
        "diagnostic_complete": True,
        "passed": True,
        "temporary_execution_directory_remaining": False,
        "private_task_or_web_content_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "official_evaluator_called": False,
        "resume_retry_skip_or_revaluation": False,
        "provenance": {
            name: "a" * 64
            for name in (
                "protocol_sha256",
                "preactivation_audit_sha256",
                "activation_sha256",
                "execution_start_sha256",
                "surface_manifest_sha256",
            )
        },
    }
    return _seal(value, "result_payload_sha256")


class V24472BoundedAdaptiveExternalGateTests(unittest.TestCase):
    def test_population_and_three_nested_deadlines_are_frozen(self) -> None:
        self.assertTrue(target._fresh_entity_vector_valid())
        self.assertEqual(len(target.QUESTIONS), 8)
        self.assertEqual(len(target._prior_questions()), 276)
        self.assertEqual(sum(map(len, target.ENTITY_GROUPS)), 64)
        self.assertEqual(target.SELECTED, target.EXECUTOR_COUNT)
        self.assertEqual(target.MODEL_SLOT_CAP, 2)
        self.assertLess(
            target.EFFECT_DEADLINE_SECONDS,
            target.WORKER_TIMEOUT_SECONDS,
        )
        self.assertLess(
            target.WORKER_TIMEOUT_SECONDS,
            target.PARENT_TIMEOUT_SECONDS,
        )
        self.assertGreaterEqual(
            min(
                target.WORKER_CLOSURE_RESERVE_SECONDS,
                target.PARENT_CLOSURE_RESERVE_SECONDS,
            ),
            target.MINIMUM_CLOSURE_RESERVE_SECONDS,
        )
        self.assertEqual(
            [set(target.neutral_task(index)) for index in range(1, 9)],
            [{"opaque_id", "question"}] * 8,
        )

    def test_protocol_is_design_only_and_persists_no_task_content(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        encoded = json.dumps(value, ensure_ascii=False)
        for ordinal in range(1, target.SELECTED + 1):
            task = target.neutral_task(ordinal)
            self.assertNotIn(task["opaque_id"], encoded)
            self.assertNotIn(task["question"], encoded)
        self.assertTrue(
            value["authorization"][
                "one_fresh_bounded_adaptive_external_probe_design"
            ]
        )
        self.assertFalse(value["authorization"]["external_probe_launch"])
        self.assertFalse(value["authorization"]["paired_dev64_or_exact220"])
        self.assertFalse(value["task_contract"]["v24466_population_rerun"])

    def test_resealed_protocol_tamper_fails_closed(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        cases = (
            (
                "population",
                lambda item: item["task_contract"].__setitem__(
                    "v24466_population_rerun", True
                ),
            ),
            (
                "worker_deadline",
                lambda item: item["budget"].__setitem__(
                    "worker_timeout_seconds", 140.0
                ),
            ),
            (
                "supervisor",
                lambda item: item["mechanism"].__setitem__(
                    "worker_process_group_hard_cutoff", False
                ),
            ),
            (
                "launch",
                lambda item: item["authorization"].__setitem__(
                    "external_probe_launch", True
                ),
            ),
        )
        for name, alter in cases:
            with self.subTest(name=name):
                changed = copy.deepcopy(value)
                alter(changed)
                _seal(changed, "protocol_payload_sha256")
                with self.assertRaises(RuntimeError):
                    target.validate_protocol(value=changed)

    def test_worker_uses_hard_total_wall_factories_and_stage_callback(self) -> None:
        captured: dict = {}
        events: list[str] = []
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            base = Path(temporary)
            directory = base / "task"
            checkpoint = base / "checkpoint"
            slots = base / "slots"
            directory.mkdir()
            checkpoint.mkdir()
            slots.mkdir()
            args = argparse.Namespace(
                ordinal="1",
                output_root=str(base),
                directory=str(directory),
                checkpoint_directory=str(checkpoint),
                slots=str(slots),
                effect_deadline_monotonic=str(
                    time.monotonic() + target.EFFECT_DEADLINE_SECONDS
                ),
                worker_deadline_monotonic=None,
            )

            def invoke_worker(task, **kwargs):
                captured.update({"task": task, **kwargs})
                kwargs["model_factory"](events.append)
                kwargs["search_factory"](events.append)

            with (
                patch.dict(
                    os.environ,
                    {"DEEPWIDE_EXPECTED_SUPERVISOR_PID": str(os.getpid())},
                ),
                patch.object(
                    target,
                    "validate_protocol",
                    return_value={"surface_manifest_sha256": "a" * 64},
                ),
                patch.object(target, "run_worker", side_effect=invoke_worker),
                patch.object(
                    target,
                    "build_hard_total_wall_model",
                    side_effect=lambda **kwargs: kwargs["stage_callback"](
                        "model_effect_started"
                    ),
                ) as model,
                patch.object(
                    target,
                    "build_hard_total_wall_search",
                    side_effect=lambda **kwargs: kwargs["stage_callback"](
                        "hosted_search_effect_started"
                    ),
                ) as search,
            ):
                target._worker(args)
        self.assertEqual(set(captured["task"]), {"opaque_id", "question"})
        self.assertEqual(captured["expected_supervisor_pid"], os.getpid())
        self.assertEqual(captured["expected_model_cap"], target.MODEL_SLOT_CAP)
        self.assertEqual(
            events, ["model_effect_started", "hosted_search_effect_started"]
        )
        self.assertEqual(model.call_args.kwargs["url"], "http://127.0.0.1:9878/responses")
        self.assertEqual(search.call_args.kwargs["url"], "http://127.0.0.1:9878/responses")

        expired = copy.copy(args)
        expired.effect_deadline_monotonic = str(time.monotonic() - 1)

        def invoke_expired(_task, **kwargs):
            with self.assertRaisesRegex(RuntimeError, "inherited effect deadline"):
                kwargs["model_factory"](lambda _stage: None)

        with (
            patch.dict(
                os.environ,
                {"DEEPWIDE_EXPECTED_SUPERVISOR_PID": str(os.getpid())},
            ),
            patch.object(
                target,
                "validate_protocol",
                return_value={"surface_manifest_sha256": "a" * 64},
            ),
            patch.object(target, "run_worker", side_effect=invoke_expired),
        ):
            target._worker(expired)

    def test_supervisor_binds_worker_group_timeout(self) -> None:
        captured: dict = {}
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            base = Path(temporary)
            directory = base / "task"
            checkpoint = base / "checkpoint"
            slots = base / "slots"
            directory.mkdir()
            checkpoint.mkdir()
            slots.mkdir()
            args = argparse.Namespace(
                ordinal="1",
                output_root=str(base),
                directory=str(directory),
                checkpoint_directory=str(checkpoint),
                slots=str(slots),
                effect_deadline_monotonic=str(
                    time.monotonic() + target.EFFECT_DEADLINE_SECONDS
                ),
                worker_deadline_monotonic=str(
                    time.monotonic() + target.WORKER_TIMEOUT_SECONDS
                ),
            )
            with patch.object(
                target,
                "supervise_and_publish",
                side_effect=lambda **kwargs: captured.update(kwargs),
            ):
                target._supervisor(args)
        self.assertGreater(captured["timeout_seconds"], 0)
        self.assertLessEqual(
            captured["timeout_seconds"], target.WORKER_TIMEOUT_SECONDS
        )
        self.assertIn("worker", captured["command"])
        deadline_index = captured["command"].index("--effect-deadline-monotonic")
        inherited_deadline = float(captured["command"][deadline_index + 1])
        self.assertGreater(inherited_deadline, time.monotonic())
        self.assertLessEqual(
            inherited_deadline - time.monotonic(),
            target.EFFECT_DEADLINE_SECONDS,
        )

        expired = copy.copy(args)
        expired.worker_deadline_monotonic = str(time.monotonic() - 1)
        expired_capture: dict = {}
        with patch.object(
            target,
            "supervise_and_publish",
            side_effect=lambda **kwargs: expired_capture.update(kwargs),
        ):
            target._supervisor(expired)
        self.assertEqual(expired_capture["timeout_seconds"], 1e-6)
        self.assertEqual(captured["expected_model_cap"], target.MODEL_SLOT_CAP)
        self.assertEqual(captured["directory"].parent, captured["checkpoint_directory"].parent)

    def test_parent_binds_bounded_supervisor_and_parent_timeout(self) -> None:
        captured: dict = {}

        def run(**kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                proof=SimpleNamespace(
                    adaptive_projection={"ordinal": 1},
                    observation={"ordinal": 1},
                    timing_receipt={"ordinal": 1},
                ),
                supervision_receipt={"ordinal": 1},
            )

        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            base = Path(temporary)
            directory = base / "task"
            checkpoint = base / "checkpoint"
            slots = base / "slots"
            directory.mkdir()
            checkpoint.mkdir()
            slots.mkdir()
            with (
                patch.object(
                    target,
                    "validate_protocol",
                    return_value={"surface_manifest_sha256": "b" * 64},
                ),
                patch.object(
                    target,
                    "run_bounded_parent_subprocess",
                    side_effect=run,
                ),
            ):
                outcome = target._run_one(
                    ROOT, base, slots, directory, checkpoint, 1
                )
        self.assertEqual(
            set(outcome), {"mechanism", "observation", "timing", "supervision"}
        )
        self.assertGreater(captured["parent_timeout_seconds"], 0)
        self.assertLessEqual(
            captured["parent_timeout_seconds"], target.PARENT_TIMEOUT_SECONDS
        )
        self.assertEqual(
            captured["expected_validator_manifest_sha256"], "b" * 64
        )
        self.assertIn("supervisor", captured["command"])
        deadline_index = captured["command"].index("--effect-deadline-monotonic")
        inherited_deadline = float(captured["command"][deadline_index + 1])
        self.assertGreater(inherited_deadline, time.monotonic())
        self.assertLessEqual(
            inherited_deadline - time.monotonic(),
            target.EFFECT_DEADLINE_SECONDS,
        )
        worker_index = captured["command"].index("--worker-deadline-monotonic")
        inherited_worker_deadline = float(captured["command"][worker_index + 1])
        self.assertGreater(inherited_worker_deadline, inherited_deadline)
        self.assertLessEqual(
            inherited_worker_deadline - time.monotonic(),
            target.WORKER_TIMEOUT_SECONDS,
        )

    def test_public_result_rejects_supervision_and_content_tamper(self) -> None:
        value = _successful_public_result()
        with (
            patch.object(target, "validate_mechanism_aggregate"),
            patch.object(target, "validate_observation_aggregate"),
            patch.object(target, "validate_stage_timing_aggregate"),
            patch.object(target, "validate_supervision_aggregate"),
        ):
            target.validate_public_result(value)
            cases = (
                (
                    "worker_timeout",
                    lambda item: item["supervision_aggregate"].__setitem__(
                        "worker_hard_timeout_tasks", 1
                    ),
                ),
                (
                    "zero_closed_validation",
                    lambda item: item["supervision_aggregate"].__setitem__(
                        "complete_validation_returned_tasks", 0
                    ),
                ),
                (
                    "private_content",
                    lambda item: item.__setitem__(
                        "private_task_or_web_content_persisted", True
                    ),
                ),
                (
                    "false_go",
                    lambda item: item.__setitem__("passed", False),
                ),
            )
            for name, alter in cases:
                with self.subTest(name=name):
                    changed = copy.deepcopy(value)
                    alter(changed)
                    _seal(changed, "result_payload_sha256")
                    with self.assertRaises(RuntimeError):
                        target.validate_public_result(changed)

    def test_runtime_source_is_label_blind(self) -> None:
        accesses, imports = target.build_audit.base._ast_findings(
            Path(target.RUNNER_MARKER)
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
