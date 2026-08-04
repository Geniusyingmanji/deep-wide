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
from scripts import v24484_separated_budget_external_gate as target  # noqa: E402


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
        "worker_wall_max_seconds": 150.0,
    }
    value = {
        "artifact_version": 1,
        "role": "v24484_separated_budget_external_result",
        "protocol_id": target.PROTOCOL_ID,
        "created_at_unix": 0,
        "selected": target.SELECTED,
        "executor_count": target.EXECUTOR_COUNT,
        "model_slot_cap": target.MODEL_SLOT_CAP,
        "effect_deadline_seconds": target.EFFECT_DEADLINE_SECONDS,
        "worker_timeout_seconds": target.WORKER_TIMEOUT_SECONDS,
        "parent_timeout_seconds": target.PARENT_TIMEOUT_SECONDS,
        "one_wave": True,
        "batch_wall_seconds": 180.0,
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


class V24484SeparatedBudgetExternalGateTests(unittest.TestCase):
    def test_population_and_phase_deadlines_are_frozen(self) -> None:
        self.assertTrue(target._fresh_entity_vector_valid())
        self.assertEqual(len(target.QUESTIONS), 8)
        self.assertEqual(len(target._prior_questions()), 292)
        self.assertEqual(sum(map(len, target.ENTITY_GROUPS)), 64)
        self.assertEqual(target.SELECTED, target.EXECUTOR_COUNT)
        self.assertEqual(
            (
                target.EFFECT_DEADLINE_SECONDS,
                target.WORKER_TIMEOUT_SECONDS,
                target.PARENT_TIMEOUT_SECONDS,
                target.BATCH_WALL_CEILING_SECONDS,
            ),
            (150.0, 220.0, 245.0, 255.0),
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
                "one_fresh_separated_budget_external_probe_design"
            ]
        )
        self.assertFalse(value["authorization"]["external_probe_launch"])
        self.assertFalse(value["authorization"]["paired_dev64_or_exact220"])
        self.assertFalse(
            value["task_contract"]["v24466_v24472_v24478_population_rerun"]
        )

    def test_resealed_protocol_tamper_fails_closed(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        cases = (
            (
                "population",
                lambda item: item["task_contract"].__setitem__(
                    "v24466_v24472_v24478_population_rerun", True
                ),
            ),
            (
                "remote_budget",
                lambda item: item["budget"].__setitem__(
                    "effect_deadline_seconds", 220.0
                ),
            ),
            (
                "lease_owner",
                lambda item: item["lease"].__setitem__("owner", "other"),
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

    def test_worker_uses_only_remote_effect_deadline(self) -> None:
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
                deadline_origin_monotonic="1000.0",
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
                patch.object(
                    target.worker_budget,
                    "remote_effect_deadline",
                    return_value=1150.0,
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
                    "build_bounded_nominal_hard_total_wall_search",
                    side_effect=lambda **kwargs: kwargs["stage_callback"](
                        "hosted_search_effect_started"
                    ),
                ) as search,
            ):
                target._worker(args)
        self.assertEqual(set(captured["task"]), {"opaque_id", "question"})
        self.assertEqual(model.call_args.kwargs["absolute_deadline"], 1150.0)
        self.assertEqual(search.call_args.kwargs["absolute_deadline"], 1150.0)
        self.assertEqual(events, ["model_effect_started", "hosted_search_effect_started"])

    def test_supervisor_passes_one_origin_to_separated_worker_budget(self) -> None:
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
                deadline_origin_monotonic="1000.0",
            )
            with patch.object(
                target.worker_budget,
                "supervise_worker_with_separated_budget",
                side_effect=lambda **kwargs: captured.update(kwargs),
            ):
                target._supervisor(args)
        self.assertEqual(captured["deadline_origin"], "1000.0")
        self.assertIn("worker", captured["worker_command"])
        self.assertNotIn(
            target.worker_budget.DEADLINE_ORIGIN_ARGUMENT,
            captured["worker_command"],
        )

    def test_parent_uses_separated_budget_adapter(self) -> None:
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
                    target.worker_budget,
                    "run_parent_with_separated_budget",
                    side_effect=run,
                ),
            ):
                outcome = target._run_one(
                    ROOT, base, slots, directory, checkpoint, 1
                )
        self.assertEqual(
            set(outcome), {"mechanism", "observation", "timing", "supervision"}
        )
        self.assertEqual(
            captured["expected_validator_manifest_sha256"], "b" * 64
        )
        self.assertIn("supervisor", captured["supervisor_command"])

    def test_public_result_rejects_supervision_and_content_tamper(self) -> None:
        value = _successful_public_result()
        with (
            patch.object(target.history, "validate_mechanism_aggregate"),
            patch.object(target.history, "validate_observation_aggregate"),
            patch.object(target.history, "validate_stage_timing_aggregate"),
            patch.object(target.history, "validate_supervision_aggregate"),
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
                    "private_content",
                    lambda item: item.__setitem__(
                        "private_task_or_web_content_persisted", True
                    ),
                ),
                ("false_go", lambda item: item.__setitem__("passed", False)),
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
