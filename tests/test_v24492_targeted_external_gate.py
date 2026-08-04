from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import v24492_targeted_external_gate as target  # noqa: E402


def _seal(value: dict, field: str) -> dict:
    value.pop(field, None)
    value[field] = payload_sha256(value)
    return value


def _successful_public_result() -> dict:
    mechanism = {
        "selected": 8,
        "exact_ordinal_vector": True,
        "passed_tasks": 8,
        "failed_tasks": 0,
        "target_plan_tasks": 1,
        "safe_change_improvement_tasks": 1,
        "positive_decision_credit_tasks": 1,
        "total_targeted_selected_source_count": 1,
        "total_additional_fetch_effects": 1,
        "total_additional_model_acquisitions": 0,
        "total_validation_memo_misses": 64,
        "total_validation_memo_hits": 64,
        "total_positive_information_gain_nats": 1.0,
        "total_epistemic_credit_nats": 1.0,
        "total_decision_credit_nats": 1.0,
        "all_effects_conserved": True,
        "all_memos_fail_closed": True,
        "all_single_validations_attested": True,
        "all_projections_consumed_validated_capabilities": True,
        "private_task_content_emitted": False,
        "privileged_evaluator_content_read": False,
    }
    observation = {
        "selected": 8,
        "slot_timeouts_lower_bound": 0,
        "provider_deadline_failures_lower_bound": 0,
        "hosted_search_deadline_failures_lower_bound": 0,
        "hard_fetch_deadline_failures_lower_bound": 0,
        "fetch_helper_failures_lower_bound": 0,
    }
    timing = {
        "parent_success_tasks": 8,
        "certificate_validation_invocations": 8,
        "recursive_historical_semantic_replay_tasks": 0,
        "parent_certificate_validation_wall_p95_seconds": 0.02,
    }
    supervision = {
        "worker_success_tasks": 8,
        "worker_hard_timeout_tasks": 0,
        "worker_nonzero_tasks": 0,
        "complete_validation_returned_tasks": 8,
        "worker_wall_max_seconds": 100.0,
    }
    value = {
        "artifact_version": 1,
        "role": "v24492_targeted_external_result",
        "protocol_id": target.PROTOCOL_ID,
        "created_at_unix": 0,
        "selected": 8,
        "executor_count": 8,
        "model_slot_cap": 2,
        "one_wave": True,
        "batch_wall_seconds": 120.0,
        "mechanism_aggregate": mechanism,
        "observation_aggregate": observation,
        "stage_timing_aggregate": timing,
        "supervision_aggregate": supervision,
        "mechanism_passed": True,
        "reliability_passed": True,
        "parent_validation_passed": True,
        "latency_passed": True,
        "passed": True,
        "temporary_execution_directory_remaining": False,
        "private_task_or_web_content_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "official_evaluator_called": False,
        "resume_retry_skip_or_revaluation": False,
        "provenance": {"protocol_sha256": "a" * 64},
    }
    return _seal(value, "result_payload_sha256")


class V24492TargetedExternalGateTests(unittest.TestCase):
    def test_population_and_phase_deadlines_are_frozen(self) -> None:
        self.assertTrue(target._fresh_entity_vector_valid())
        self.assertEqual(len(target._prior_questions()), 308)
        self.assertEqual(len(target.QUESTIONS), 8)
        self.assertEqual(sum(map(len, target.ENTITY_GROUPS)), 64)
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

    def test_protocol_is_design_only_and_contains_no_task_content(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        encoded = json.dumps(value, ensure_ascii=False)
        for ordinal in range(1, 9):
            task = target.neutral_task(ordinal)
            self.assertNotIn(task["opaque_id"], encoded)
            self.assertNotIn(task["question"], encoded)
        self.assertEqual(value["task_contract"]["prior_external_entity_count"], 2464)
        self.assertFalse(value["task_contract"]["all_prior_external_populations_rerun"])
        self.assertTrue(value["authorization"]["one_fresh_targeted_external_probe_design"])
        self.assertFalse(value["authorization"]["external_probe_launch"])
        self.assertFalse(value["authorization"]["paired_dev64_or_exact220"])
        self.assertFalse(
            value["mechanism"]["source_count_posterior_margin_and_credit_rules_relaxed"]
        )

    def test_resealed_protocol_tamper_fails_closed(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        cases = (
            lambda item: item["task_contract"].__setitem__(
                "all_prior_external_populations_rerun", True
            ),
            lambda item: item["mechanism"].__setitem__(
                "source_count_posterior_margin_and_credit_rules_relaxed", True
            ),
            lambda item: item["budget"].__setitem__(
                "maximum_targeted_search_batches_per_task", 2
            ),
            lambda item: item["authorization"].__setitem__(
                "external_probe_launch", True
            ),
        )
        for alter in cases:
            changed = copy.deepcopy(value)
            alter(changed)
            _seal(changed, "protocol_payload_sha256")
            with self.assertRaises(RuntimeError):
                target.validate_protocol(value=changed)

    def test_worker_receives_label_blind_task_and_remote_deadline(self) -> None:
        captured: dict = {}
        events: list[str] = []
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            base = Path(temporary)
            directory = base / "task"; directory.mkdir()
            checkpoint = base / "checkpoint"; checkpoint.mkdir()
            slots = base / "slots"; slots.mkdir()
            args = argparse.Namespace(
                ordinal="1", output_root=str(base), directory=str(directory),
                checkpoint_directory=str(checkpoint), slots=str(slots),
                deadline_origin_monotonic="1000.0",
            )

            def invoke(task, **kwargs):
                captured.update({"task": task, **kwargs})
                kwargs["model_factory"](events.append)
                kwargs["search_factory"](events.append)

            with (
                patch.dict(os.environ, {"DEEPWIDE_EXPECTED_SUPERVISOR_PID": str(os.getpid())}),
                patch.object(target, "validate_protocol", return_value={"surface_manifest_sha256": "a" * 64}),
                patch.object(target.worker_budget, "remote_effect_deadline", return_value=1150.0),
                patch.object(target, "run_targeted_worker", side_effect=invoke),
                patch.object(target, "build_hard_total_wall_model", side_effect=lambda **kwargs: kwargs["stage_callback"]("model_effect_started")) as model,
                patch.object(target, "build_bounded_nominal_hard_total_wall_search", side_effect=lambda **kwargs: kwargs["stage_callback"]("hosted_search_effect_started")) as search,
            ):
                target._worker(args)
        self.assertEqual(set(captured["task"]), {"opaque_id", "question"})
        self.assertEqual(model.call_args.kwargs["absolute_deadline"], 1150.0)
        self.assertEqual(search.call_args.kwargs["absolute_deadline"], 1150.0)
        self.assertEqual(events, ["model_effect_started", "hosted_search_effect_started"])

    def test_supervisor_and_parent_use_targeted_separated_adapters(self) -> None:
        captured_supervisor: dict = {}
        captured_parent: dict = {}
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            base = Path(temporary)
            directory = base / "task"; directory.mkdir()
            checkpoint = base / "checkpoint"; checkpoint.mkdir()
            slots = base / "slots"; slots.mkdir()
            args = argparse.Namespace(
                ordinal="1", output_root=str(base), directory=str(directory),
                checkpoint_directory=str(checkpoint), slots=str(slots),
                deadline_origin_monotonic="1000.0",
            )
            with patch.object(
                target, "supervise_targeted_worker_with_separated_budget",
                side_effect=lambda **kwargs: captured_supervisor.update(kwargs),
            ):
                target._supervisor(args)
            with (
                patch.object(target, "validate_protocol", return_value={"surface_manifest_sha256": "b" * 64}),
                patch.object(
                    target, "run_targeted_parent_with_separated_budget",
                    side_effect=lambda **kwargs: captured_parent.update(kwargs)
                    or SimpleNamespace(
                        proof=SimpleNamespace(
                            adaptive_projection={"ordinal": 1},
                            observation={"ordinal": 1},
                            timing_receipt={"ordinal": 1},
                        ),
                        supervision_receipt={"ordinal": 1},
                    ),
                ),
            ):
                outcome = target._run_one(ROOT, base, slots, directory, checkpoint, 1)
        self.assertEqual(captured_supervisor["deadline_origin"], "1000.0")
        self.assertIn("worker", captured_supervisor["worker_command"])
        self.assertEqual(captured_parent["expected_validator_manifest_sha256"], "b" * 64)
        self.assertEqual(set(outcome), {"mechanism", "observation", "timing", "supervision"})

    def test_mechanism_gate_requires_targeted_safe_change_and_decision_credit(self) -> None:
        passing = _successful_public_result()["mechanism_aggregate"]
        self.assertTrue(target._mechanism_passed(passing))
        for field in (
            "target_plan_tasks", "safe_change_improvement_tasks",
            "positive_decision_credit_tasks", "total_decision_credit_nats",
        ):
            changed = dict(passing)
            changed[field] = 0
            self.assertFalse(target._mechanism_passed(changed), field)

    def test_public_result_rejects_false_go_and_private_content(self) -> None:
        value = _successful_public_result()
        with (
            patch.object(target, "validate_targeted_aggregate", side_effect=lambda item: item),
            patch.object(target, "validate_observation_aggregate", side_effect=lambda item, **_: item),
            patch.object(target, "validate_stage_timing_aggregate", side_effect=lambda item: item),
            patch.object(target, "validate_supervision_aggregate", side_effect=lambda item: item),
        ):
            target.validate_public_result(value)
            for alter in (
                lambda item: item.__setitem__("passed", False),
                lambda item: item.__setitem__("private_task_or_web_content_persisted", True),
                lambda item: item["mechanism_aggregate"].__setitem__("safe_change_improvement_tasks", 0),
            ):
                changed = copy.deepcopy(value)
                alter(changed)
                _seal(changed, "result_payload_sha256")
                with self.assertRaises(RuntimeError):
                    target.validate_public_result(changed)

    def test_runtime_source_is_label_blind(self) -> None:
        accesses, imports = target.build_audit.ast_findings(Path(target.RUNNER_MARKER))
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
