from __future__ import annotations

import argparse
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import v24466_single_validation_adaptive_external_gate as target  # noqa: E402


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
        "capability_observation_tasks": target.SELECTED,
        "capability_adaptive_projection_tasks": target.SELECTED,
        "failure_lower_bound_observation_tasks": 0,
        "recursive_historical_semantic_replay_tasks": 0,
        "parent_certificate_validation_wall_p95_seconds": 0.02,
    }
    value = {
        "artifact_version": 1,
        "role": "v24466_single_validation_external_result",
        "protocol_id": target.PROTOCOL_ID,
        "created_at_unix": 0,
        "selected": target.SELECTED,
        "executor_count": target.EXECUTOR_COUNT,
        "model_slot_cap": target.MODEL_SLOT_CAP,
        "effect_deadline_seconds": target.EFFECT_DEADLINE_SECONDS,
        "parent_timeout_seconds": target.PARENT_TIMEOUT_SECONDS,
        "terminal_reserve_seconds": target.TERMINAL_RESERVE_SECONDS,
        "one_wave": True,
        "batch_wall_seconds": 100.0,
        "mechanism_aggregate": mechanism,
        "observation_aggregate": observation,
        "stage_timing_aggregate": timing,
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


class V24466SingleValidationAdaptiveExternalGateTests(unittest.TestCase):
    def test_population_capacity_and_terminal_reserve_are_frozen(self) -> None:
        self.assertTrue(target._fresh_entity_vector_valid())
        self.assertEqual(len(target.QUESTIONS), 8)
        self.assertEqual(len(target._prior_questions()), 268)
        self.assertEqual(sum(map(len, target.ENTITY_GROUPS)), 64)
        self.assertEqual(target.SELECTED, target.EXECUTOR_COUNT)
        self.assertEqual(target.MODEL_SLOT_CAP, 2)
        self.assertGreaterEqual(
            target.TERMINAL_RESERVE_SECONDS,
            target.MINIMUM_TERMINAL_RESERVE_SECONDS,
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
                "one_fresh_single_validation_external_probe_design"
            ]
        )
        self.assertFalse(value["authorization"]["external_probe_launch"])
        self.assertFalse(value["authorization"]["paired_dev64_or_exact220"])
        self.assertTrue(value["budget"]["one_wave"])

    def test_resealed_protocol_tamper_fails_closed(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        cases = (
            ("discovery", lambda item: item["discovery_partition"].__setitem__("seed_sha256_vector", list(reversed(item["discovery_partition"]["seed_sha256_vector"])))),
            ("lease", lambda item: item["lease"].__setitem__("owner", "another-owner")),
            ("capacity", lambda item: item["provider"].__setitem__("executor_count", 7)),
            ("reserve", lambda item: item["budget"].__setitem__("terminal_reserve_seconds", 20)),
            ("launch", lambda item: item["authorization"].__setitem__("external_probe_launch", True)),
        )
        for name, alter in cases:
            with self.subTest(name=name):
                changed = copy.deepcopy(value)
                alter(changed)
                _seal(changed, "protocol_payload_sha256")
                with self.assertRaises(RuntimeError):
                    target.validate_protocol(value=changed)

    def test_child_path_uses_single_validation_persistence(self) -> None:
        calls: list[dict] = []
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            base = Path(temporary)
            directory = base / "task"
            slots = base / "slots"
            directory.mkdir()
            slots.mkdir()
            args = argparse.Namespace(
                ordinal="1",
                output_root=str(base),
                directory=str(directory),
                slots=str(slots),
            )

            def invoke_action(**kwargs):
                kwargs["action"]()

            def persist(task, **kwargs):
                calls.append({"task": task, **kwargs})

            with (
                patch.object(
                    target,
                    "validate_protocol",
                    return_value={"surface_manifest_sha256": "a" * 64},
                ),
                patch.object(
                    target,
                    "run_child_with_terminal_receipt",
                    side_effect=invoke_action,
                ),
                patch.object(
                    target,
                    "run_and_persist_single_validation_adaptive_task",
                    side_effect=persist,
                ),
            ):
                target._child(args)
        self.assertEqual(len(calls), 1)
        self.assertEqual(set(calls[0]["task"]), {"opaque_id", "question"})
        self.assertEqual(calls[0]["expected_model_cap"], target.MODEL_SLOT_CAP)
        self.assertEqual(calls[0]["validator_manifest_sha256"], "a" * 64)

    def test_parent_runner_binds_one_wave_timeout_and_manifest(self) -> None:
        captured: dict = {}

        def run(**kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                adaptive_projection={"ordinal": 1},
                observation={"ordinal": 1},
                timing_receipt={"ordinal": 1},
            )

        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            base = Path(temporary)
            directory = base / "task"
            slots = base / "slots"
            directory.mkdir()
            slots.mkdir()
            with (
                patch.object(
                    target,
                    "validate_protocol",
                    return_value={"surface_manifest_sha256": "b" * 64},
                ),
                patch.object(
                    target,
                    "run_proof_carrying_adaptive_timed_subprocess",
                    side_effect=run,
                ),
            ):
                outcome = target._run_one(ROOT, base, slots, directory, 1)
        self.assertEqual(set(outcome), {"mechanism", "observation", "timing"})
        self.assertEqual(captured["timeout_seconds"], target.PARENT_TIMEOUT_SECONDS)
        self.assertEqual(captured["expected_model_cap"], target.MODEL_SLOT_CAP)
        self.assertEqual(captured["expected_validator_manifest_sha256"], "b" * 64)
        self.assertEqual(captured["command"][3], str(ROOT / target.RUNNER_MARKER))

    def test_public_result_rejects_content_replay_and_gate_tamper(self) -> None:
        value = _successful_public_result()
        with (
            patch.object(target, "validate_mechanism_aggregate"),
            patch.object(target, "validate_observation_aggregate"),
            patch.object(target, "validate_stage_timing_aggregate"),
        ):
            target.validate_public_result(value)
            cases = (
                ("private_content", lambda item: item.__setitem__("private_task_or_web_content_persisted", True)),
                ("recursive_replay", lambda item: item["stage_timing_aggregate"].__setitem__("recursive_historical_semantic_replay_tasks", 1)),
                ("two_waves", lambda item: item.__setitem__("one_wave", False)),
                ("false_go", lambda item: item.__setitem__("passed", False)),
            )
            for name, alter in cases:
                with self.subTest(name=name):
                    changed = copy.deepcopy(value)
                    alter(changed)
                    _seal(changed, "result_payload_sha256")
                    with self.assertRaises(RuntimeError):
                        target.validate_public_result(changed)

    def test_resealed_activation_authorization_tamper_fails(self) -> None:
        protocol = {"surface_manifest_sha256": "c" * 64}
        watchers = {"watcher": "unchanged"}
        with (
            patch.object(target, "validate_protocol", return_value=protocol),
            patch.object(
                target,
                "validate_preaudit",
                return_value={"protected_watchers": watchers},
            ),
            patch.object(target, "_future", return_value=True),
            patch.object(target, "lease_observation", return_value={"active": False}),
            patch.object(target, "_port_listening", return_value=True),
            patch.object(target, "sha256", return_value="d" * 64),
        ):
            value = target.build_activation(now=0)

        changed = copy.deepcopy(value)
        changed["authorization"]["benchmark_launch"] = True
        _seal(changed, "activation_payload_sha256")
        with (
            patch.object(target, "_read", return_value=changed),
            patch.object(target, "validate_protocol", return_value=protocol),
            patch.object(target, "validate_preaudit"),
            patch.object(target, "protected_watcher_snapshot", return_value=watchers),
            patch.object(target, "sha256", return_value="d" * 64),
        ):
            with self.assertRaises(RuntimeError):
                target.validate_activation()

    def test_runtime_source_is_label_blind(self) -> None:
        accesses, imports = target.build_audit.base._ast_findings(
            Path(target.RUNNER_MARKER)
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
